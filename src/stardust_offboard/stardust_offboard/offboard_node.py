import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from mavros_msgs.srv import CommandBool, SetMode
from mavros_msgs.msg import State

class OffboardControl(Node):

    def __init__(self):
        super().__init__('offboard_control')

        self.state_sub = self.create_subscription(
            State,
            '/mavros/state',
            self.state_cb,
            10)

        self.local_pos_pub = self.create_publisher(
            PoseStamped,
            '/mavros/setpoint_position/local',
            10)

        self.arming_client = self.create_client(CommandBool, '/mavros/cmd/arming')
        self.set_mode_client = self.create_client(SetMode, '/mavros/set_mode')

        self.current_state = State()

        self.timer = self.create_timer(0.05, self.timer_callback)  # 20 Hz

        self.pose = PoseStamped()
        self.pose.pose.position.x = 0.0
        self.pose.pose.position.y = 0.0
        self.pose.pose.position.z = 3.0

        self.counter = 0
        self.offboard_set = False
        self.armed = False

    def state_cb(self, msg):
        self.current_state = msg

    def timer_callback(self):

        self.local_pos_pub.publish(self.pose)

        if not self.current_state.connected:
            return

        if self.counter < 20:
            self.counter += 1
            return

        if not self.offboard_set:
            req = SetMode.Request()
            req.custom_mode = "OFFBOARD"
            self.set_mode_client.call_async(req)
            self.get_logger().info("Switching to OFFBOARD")
            self.offboard_set = True
            return

        if not self.armed:
            arm_req = CommandBool.Request()
            arm_req.value = True
            self.arming_client.call_async(arm_req)
            self.get_logger().info("Arming")
            self.armed = True
            return

        # Hover for 10 seconds
        if self.counter < 220:
            self.counter += 1
            return

        # Switch to AUTO.LAND
        req = SetMode.Request()
        req.custom_mode = "AUTO.LAND"
        self.set_mode_client.call_async(req)
        self.get_logger().info("Landing...")

def main(args=None):
    rclpy.init(args=args)
    node = OffboardControl()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
