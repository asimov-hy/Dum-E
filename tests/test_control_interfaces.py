from pathlib import Path

import pytest

from dume.control import (
    CalibrationError,
    ConnectionError,
    ControlSession,
    HardwareError,
    JointLimitError,
    MockArmDriver,
    MockTeleopDriver,
    MotorStallError,
    PoseStore,
    ReplayService,
)


def test_mock_arm_driver_connection_and_joint_readback() -> None:
    driver = MockArmDriver()

    assert not driver.is_connected()

    driver.connect()
    moved = driver.move_joints([0.0, 0.1, 0.2], speed=0.25)

    assert driver.is_connected()
    assert moved
    assert driver.read_joints() == [0.0, 0.1, 0.2]
    assert driver.last_speed == 0.25

    driver.disconnect()

    assert not driver.is_connected()


def test_mock_arm_driver_requires_connection() -> None:
    driver = MockArmDriver()

    with pytest.raises(ConnectionError):
        driver.move_joints([0.0])


def test_control_exceptions_are_typed_and_exported() -> None:
    assert issubclass(ConnectionError, HardwareError)
    assert issubclass(MotorStallError, HardwareError)
    assert issubclass(JointLimitError, HardwareError)
    assert issubclass(CalibrationError, HardwareError)
    assert str(ConnectionError("offline")) == "offline"


def test_mock_teleop_driver_start_stop_state() -> None:
    driver = MockTeleopDriver()

    assert not driver.is_active()

    driver.start()

    assert driver.is_active()

    driver.stop()

    assert not driver.is_active()


def test_replay_service_executes_pose_with_driver(tmp_path: Path) -> None:
    session = ControlSession.load(tmp_path)
    store = PoseStore(session)
    replay = ReplayService(session, store)
    driver = MockArmDriver()
    driver.connect()

    assert replay.execute_pose("home", driver)
    assert driver.read_joints() == [0.0] * 6


def test_replay_service_executes_motion_with_driver(tmp_path: Path) -> None:
    session = ControlSession.load(tmp_path)
    store = PoseStore(session)
    replay = ReplayService(session, store)
    driver = MockArmDriver()
    driver.connect()

    store.save_pose("inspection_pose", [0.0, 0.1, 0.2, 0.0, 0.0, 0.0])
    store.scaffold_motion("inspection_cycle", ["home", "inspection_pose"])

    assert replay.execute_motion("inspection_cycle", driver)
    assert driver.read_joints() == [0.0, 0.1, 0.2, 0.0, 0.0, 0.0]
