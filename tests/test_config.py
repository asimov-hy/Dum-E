from pathlib import Path

from dum_e.control.recording import PoseStore
from dum_e.control.session import ControlSession


def test_session_bootstrap_creates_default_files(tmp_path: Path) -> None:
    session = ControlSession.load(tmp_path)

    assert session.paths.hardware_config.exists()
    assert session.paths.calibration_config.exists()
    assert session.paths.poses_file.exists()
    assert session.status_summary()["motor_count"] == 6


def test_pose_store_scaffolds_motion(tmp_path: Path) -> None:
    session = ControlSession.load(tmp_path)
    store = PoseStore(session)

    store.save_pose("inspection_pose", [0.0, 0.1, 0.2, 0.0, 0.0, 0.0])
    motion = store.scaffold_motion("inspection_cycle", ["home", "inspection_pose"])

    assert motion.name == "inspection_cycle"
    assert len(motion.steps) == 2
    assert (session.paths.motions_dir / "inspection_cycle.json").exists()
