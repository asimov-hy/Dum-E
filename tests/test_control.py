"""Tests for the control layer using MockBus (no hardware required)."""

from pathlib import Path

import pytest

from dum_e.config import CalibrationConfig, JointCalibration
from dum_e.control.arm import ArmController, CENTER_POSITION, STEPS_PER_DEG
from dum_e.control.bus import MockBus
from dum_e.control.motors import MotorsService
from dum_e.control.recording import PoseStore
from dum_e.control.replay import ReplayService
from dum_e.control.session import ControlSession
from dum_e.control.teleop import TeleopService


# -- helpers -------------------------------------------------------------------


def _make_session(tmp_path: Path) -> ControlSession:
    return ControlSession.load(tmp_path)


def _connect_mock(session: ControlSession) -> ArmController:
    bus = MockBus()
    return session.connect_arm(bus=bus)


# -- MockBus -------------------------------------------------------------------


class TestMockBus:
    def test_connect_disconnect(self) -> None:
        bus = MockBus()
        assert not bus.is_connected
        bus.connect()
        assert bus.is_connected
        bus.disconnect()
        assert not bus.is_connected

    def test_ping_returns_true_for_present_ids(self) -> None:
        bus = MockBus()
        bus.connect()
        assert bus.ping(1) is True
        assert bus.ping(99) is False

    def test_read_write_position(self) -> None:
        bus = MockBus()
        bus.connect()
        assert bus.read_position(1) == 2048  # default center
        bus.write_position(1, 3000)
        assert bus.read_position(1) == 3000

    def test_write_motor_id(self) -> None:
        bus = MockBus()
        bus.connect()
        bus.write_position(1, 1000)
        bus.write_motor_id(1, 10)
        assert bus.ping(10) is True
        assert bus.ping(1) is False
        assert bus.read_position(10) == 1000

    def test_operations_require_connection(self) -> None:
        bus = MockBus()
        with pytest.raises(ConnectionError):
            bus.read_position(1)


# -- ArmController -------------------------------------------------------------


class TestArmController:
    def test_read_joints_at_center(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        arm = _connect_mock(session)
        joints = arm.read_joints()
        assert len(joints) == 6
        assert all(j == 0.0 for j in joints)  # center position = 0 deg

    def test_move_joints(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        arm = _connect_mock(session)
        arm.enable()
        arm.move_joints([10.0, 20.0, 30.0, 0.0, 0.0, 0.0])
        joints = arm.read_joints()
        assert abs(joints[0] - 10.0) < 0.1
        assert abs(joints[1] - 20.0) < 0.1
        assert abs(joints[2] - 30.0) < 0.1

    def test_move_requires_enable(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        arm = _connect_mock(session)
        with pytest.raises(RuntimeError, match="enabled"):
            arm.move_joints([0.0] * 6)

    def test_enable_disable(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        arm = _connect_mock(session)
        assert not arm.is_enabled
        arm.enable()
        assert arm.is_enabled
        arm.disable()
        assert not arm.is_enabled

    def test_jog_joint(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        arm = _connect_mock(session)
        arm.enable()
        new_pos = arm.jog_joint(0, 5.0)
        assert abs(new_pos - 5.0) < 0.1
        new_pos = arm.jog_joint(0, -3.0)
        assert abs(new_pos - 2.0) < 0.1

    def test_jog_respects_limits(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        # Set limits on the first joint
        session.calibration = CalibrationConfig(
            home_pose="home",
            joints=[
                JointCalibration(motor_name="shoulder_pan", min_deg=-10.0, max_deg=10.0),
            ],
        )
        arm = _connect_mock(session)
        arm.enable()
        new_pos = arm.jog_joint(0, 50.0)
        assert new_pos <= 10.0

    def test_disconnect_disables(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        arm = _connect_mock(session)
        arm.enable()
        assert arm.is_enabled
        arm.disconnect()
        assert not arm.is_enabled


# -- MotorsService -------------------------------------------------------------


class TestMotorsService:
    def test_scan_with_mock_bus(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        _connect_mock(session)
        motors = MotorsService(session)
        records = motors.scan()
        assert len(records) == 6
        assert all(r.status == "found" for r in records)

    def test_scan_without_hardware(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        motors = MotorsService(session)
        records = motors.scan()
        assert all(r.status == "configured" for r in records)

    def test_set_motor_id_with_mock(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        _connect_mock(session)
        motors = MotorsService(session)
        updated = motors.set_motor_id(name="gripper", to_id=10)
        assert updated.motor_id == 10
        # Config file should be updated
        reloaded = ControlSession.load(tmp_path)
        gripper = next(m for m in reloaded.hardware.motors if m.name == "gripper")
        assert gripper.motor_id == 10

    def test_scan_detects_missing_motor(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        bus = MockBus(_present_ids={1, 2, 3, 4, 5})  # ID 6 missing
        session.connect_arm(bus=bus)
        motors = MotorsService(session)
        records = motors.scan()
        gripper = next(r for r in records if r.name == "gripper")
        assert gripper.status == "missing"


# -- PoseStore -----------------------------------------------------------------


class TestPoseCapture:
    def test_capture_pose_from_arm(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        arm = _connect_mock(session)
        arm.enable()
        arm.move_joints([10.0, 20.0, 30.0, 0.0, 0.0, 0.0])
        store = PoseStore(session)
        joints = store.capture_pose("test_pose", arm)
        assert len(joints) == 6
        assert abs(joints[0] - 10.0) < 0.1
        # Pose should be persisted
        loaded = store.load_pose("test_pose")
        assert loaded == joints


# -- ReplayService -------------------------------------------------------------


class TestReplayExecution:
    def test_execute_pose(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        arm = _connect_mock(session)
        arm.enable()
        store = PoseStore(session)
        store.save_pose("target", [15.0, 25.0, 35.0, 0.0, 0.0, 0.0])
        replay = ReplayService(session, store)
        joints = replay.execute_pose("target", arm)
        assert joints == [15.0, 25.0, 35.0, 0.0, 0.0, 0.0]
        current = arm.read_joints()
        assert abs(current[0] - 15.0) < 0.1

    def test_execute_motion(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        arm = _connect_mock(session)
        arm.enable()
        store = PoseStore(session)
        store.save_pose("a", [10.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        store.save_pose("b", [20.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        store.scaffold_motion("ab_motion", ["a", "b"])
        replay = ReplayService(session, store)
        replay.execute_motion("ab_motion", arm)
        # Arm should be at last pose
        current = arm.read_joints()
        assert abs(current[0] - 20.0) < 0.1

    def test_pose_plan_still_works(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        store = PoseStore(session)
        replay = ReplayService(session, store)
        plan = replay.pose_plan("home")
        assert "home" in plan


# -- TeleopService -------------------------------------------------------------


class TestTeleop:
    def test_enable_disable_gating(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        arm = _connect_mock(session)
        teleop = TeleopService(arm)
        assert not teleop.is_enabled
        teleop.enable()
        assert teleop.is_enabled
        teleop.disable()
        assert not teleop.is_enabled

    def test_jog_requires_enable(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        arm = _connect_mock(session)
        teleop = TeleopService(arm)
        with pytest.raises(RuntimeError):
            teleop.jog_positive()

    def test_jog_positive_negative(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        arm = _connect_mock(session)
        teleop = TeleopService(arm)
        teleop.enable()
        pos = teleop.jog_positive()
        assert pos > 0
        pos = teleop.jog_negative()
        assert abs(pos) < 0.1  # back near zero

    def test_select_joint(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        arm = _connect_mock(session)
        teleop = TeleopService(arm)
        name = teleop.select_joint(3)
        assert name == "wrist_pitch"

    def test_step_size_clamped(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        arm = _connect_mock(session)
        teleop = TeleopService(arm)
        actual = teleop.set_step_size(100.0)
        assert actual == 5.0
        actual = teleop.set_step_size(0.01)
        assert actual == 0.1


# -- ControlSession lifecycle --------------------------------------------------


class TestSessionLifecycle:
    def test_connect_and_require_arm(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        with pytest.raises(RuntimeError):
            session.require_arm()
        arm = _connect_mock(session)
        assert session.require_arm() is arm

    def test_disconnect_arm(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        _connect_mock(session)
        session.disconnect_arm()
        assert session.arm is None

    def test_session_data_survives_restart(self, tmp_path: Path) -> None:
        session = _make_session(tmp_path)
        store = PoseStore(session)
        store.save_pose("my_pose", [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        # Reload from disk
        session2 = ControlSession.load(tmp_path)
        store2 = PoseStore(session2)
        loaded = store2.load_pose("my_pose")
        assert loaded == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
