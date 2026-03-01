import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from mavros_msgs.srv import CommandBool, SetMode
from mavros_msgs.msg import State
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

class OffboardControl(Node):

    def __init__(self):
        super().__init__('offboard_control')

        # ---------------- Subscribers ----------------
        self.state_sub = self.create_subscription(
            State,
            '/mavros/state',
            self.state_cb,
            10)

        # NEW: Subscribe to local position for altitude
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        self.local_pos_sub = self.create_subscription(
            PoseStamped,
            '/mavros/local_position/pose',
            self.pose_cb,
            qos_profile)

        # ---------------- Publisher ----------------
        self.local_pos_pub = self.create_publisher(
            PoseStamped,
            '/mavros/setpoint_position/local',
            10)

        # ---------------- Service Clients ----------------
        self.arming_client = self.create_client(CommandBool, '/mavros/cmd/arming')
        self.set_mode_client = self.create_client(SetMode, '/mavros/set_mode')

        self.current_state = State()
        self.current_altitude = 0.0  # NEW

        # Timer 20Hz (required for OFFBOARD)
        self.timer = self.create_timer(0.05, self.timer_callback)

        # Target pose (5 meters)
        self.pose = PoseStamped()
        self.pose.pose.position.x = 0.0
        self.pose.pose.position.y = 0.0
        self.pose.pose.position.z = 5.0

        # State machine variables
        self.setpoint_counter = 0
        self.hover_counter = 0
        self.phase = "INIT"

    # ---------------- Callbacks ----------------
    def state_cb(self, msg):
        self.current_state = msg

    def pose_cb(self, msg):
        self.current_altitude = msg.pose.position.z

    # ---------------- Main Timer Logic ----------------
    def timer_callback(self):

        # Always publish setpoint
        self.local_pos_pub.publish(self.pose)

        if not self.current_state.connected:
            return

        # ---------------- INIT PHASE ----------------
        if self.phase == "INIT":
            self.setpoint_counter += 1

            if self.setpoint_counter > 20:
                mode_req = SetMode.Request()
                mode_req.custom_mode = "OFFBOARD"
                self.set_mode_client.call_async(mode_req)
                self.get_logger().info("Switching to OFFBOARD")
                self.phase = "OFFBOARD"
            return

        # ---------------- SET OFFBOARD ----------------
        if self.phase == "OFFBOARD":
            if self.current_state.mode == "OFFBOARD":
                arm_req = CommandBool.Request()
                arm_req.value = True
                self.arming_client.call_async(arm_req)
                self.get_logger().info("Arming")
                self.phase = "ARMING"
            return

        # ---------------- ARMING ----------------
        if self.phase == "ARMING":
            if self.current_state.armed:
                self.get_logger().info("Taking off to 5 meters")
                self.phase = "TAKEOFF"
            return

        # ---------------- TAKEOFF ----------------
        if self.phase == "TAKEOFF":

            # Wait until altitude reaches 4.8m
            if self.current_altitude >= 4.8:
                self.get_logger().info("Reached 5m. Hovering 10 seconds.")
                self.hover_counter = 0
                self.phase = "HOVER"
            return

        # ---------------- HOVER ----------------
        if self.phase == "HOVER":

            self.hover_counter += 1

            # 20Hz × 200 ≈ 10 seconds
            if self.hover_counter > 200:
                land_req = SetMode.Request()
                land_req.custom_mode = "AUTO.LAND"
                self.set_mode_client.call_async(land_req)
                self.get_logger().info("Landing...")
                self.phase = "LANDING"
            return

        # ---------------- LANDING ----------------
        if self.phase == "LANDING":
            if not self.current_state.armed:
                self.get_logger().info("Disarmed. Motors stopped.")
                self.phase = "DONE"
            return


def main(args=None):
    rclpy.init(args=args)
    node = OffboardControl()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
