from __future__ import annotations

import argparse
from pathlib import Path

from dume.control import (
    CalibrationService,
    ControlSession,
    MotorsService,
    PoseStore,
    ReplayService,
    TeleopService,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dum-E utility-first LeRobot toolkit")
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root containing config/ and data/ directories",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Create default utility config and data files")
    subparsers.add_parser("status", help="Show config and storage summary")

    motors_parser = subparsers.add_parser("motors", help="Motor ID utilities")
    motors_subparsers = motors_parser.add_subparsers(dest="motors_command", required=True)
    motors_subparsers.add_parser("scan", help="Show expected motor map from config")
    set_id_parser = motors_subparsers.add_parser("set-id", help="Update a motor ID in config")
    target_group = set_id_parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--name", help="Motor name to update")
    target_group.add_argument("--from-id", type=int, help="Current motor ID to update")
    set_id_parser.add_argument("--to-id", type=int, required=True, help="New motor ID")

    calibrate_parser = subparsers.add_parser("calibrate", help="Calibration metadata utilities")
    calibrate_subparsers = calibrate_parser.add_subparsers(
        dest="calibrate_command", required=True
    )
    calibrate_subparsers.add_parser("init", help="Sync calibration joints from hardware config")
    calibrate_subparsers.add_parser("show", help="Show current calibration metadata")

    subparsers.add_parser("teleop", help="Show planned teleop controls and safety defaults")

    poses_parser = subparsers.add_parser("poses", help="Named pose storage utilities")
    poses_subparsers = poses_parser.add_subparsers(dest="poses_command", required=True)
    poses_subparsers.add_parser("list", help="List saved poses")
    save_pose_parser = poses_subparsers.add_parser("save", help="Save a pose from joint values")
    save_pose_parser.add_argument("name", help="Pose name in snake_case")
    save_pose_parser.add_argument(
        "--joints",
        required=True,
        help="Comma-separated joint values, e.g. 0,0.1,0.2,0,0,0",
    )

    motions_parser = subparsers.add_parser("motions", help="Motion storage utilities")
    motions_subparsers = motions_parser.add_subparsers(dest="motions_command", required=True)
    motions_subparsers.add_parser("list", help="List stored motions")
    scaffold_parser = motions_subparsers.add_parser(
        "scaffold", help="Create a motion skeleton from named poses"
    )
    scaffold_parser.add_argument("name", help="Motion name in snake_case")
    scaffold_parser.add_argument(
        "--poses",
        required=True,
        help="Comma-separated pose names, e.g. home,rack_approach,dock_approach",
    )

    replay_parser = subparsers.add_parser("replay", help="Inspect replay plans")
    replay_subparsers = replay_parser.add_subparsers(dest="replay_command", required=True)
    replay_pose_parser = replay_subparsers.add_parser("pose", help="Inspect a pose replay plan")
    replay_pose_parser.add_argument("name", help="Saved pose name")
    replay_motion_parser = replay_subparsers.add_parser(
        "motion", help="Inspect a motion replay plan"
    )
    replay_motion_parser.add_argument("name", help="Saved motion name")

    return parser


def parse_joint_values(raw: str) -> list[float]:
    return [float(part.strip()) for part in raw.split(",") if part.strip()]


def app() -> None:
    args = build_parser().parse_args()
    session = ControlSession.load(Path(args.project_root))
    pose_store = PoseStore(session)
    replay_service = ReplayService(session, pose_store)

    if args.command == "init":
        session.bootstrap()
        print(f"Initialized Dum-E utility project at {session.paths.root}")
        return

    if args.command == "status":
        summary = session.status_summary()
        print(f"Project root: {session.paths.root}")
        print(f"Robot: {summary['robot_name']}")
        print(f"Serial: {summary['port']} @ {summary['baudrate']}")
        print(f"Configured motors: {summary['motor_count']}")
        print(f"Calibration joints: {summary['calibration_joint_count']}")
        print(f"Saved poses: {summary['pose_count']}")
        print(f"Saved motions: {summary['motion_count']}")
        return

    if args.command == "motors":
        motors = MotorsService(session)
        if args.motors_command == "scan":
            for record in motors.scan():
                print(
                    f"{record.name}: expected_id={record.expected_id}, "
                    f"model={record.model}, status={record.status}"
                )
            return
        if args.motors_command == "set-id":
            updated = motors.set_motor_id(name=args.name, from_id=args.from_id, to_id=args.to_id)
            print(f"Updated motor '{updated.name}' to ID {updated.motor_id}")
            return

    if args.command == "calibrate":
        calibration = CalibrationService(session)
        if args.calibrate_command == "init":
            synced = calibration.sync_from_hardware()
            print(f"Calibration template synced for {len(synced.joints)} joints")
            return
        if args.calibrate_command == "show":
            current = calibration.current()
            print(f"Home pose: {current.home_pose}")
            for joint in current.joints:
                limits = f"{joint.min_deg}..{joint.max_deg}"
                print(
                    f"{joint.motor_name}: offset_deg={joint.offset_deg}, "
                    f"inverted={joint.inverted}, limits={limits}"
                )
            return

    if args.command == "teleop":
        teleop = TeleopService()
        print(teleop.describe())
        return

    if args.command == "poses":
        if args.poses_command == "list":
            for name, joints in pose_store.list_poses().items():
                print(f"{name}: joints={len(joints)}")
            return
        if args.poses_command == "save":
            joints = parse_joint_values(args.joints)
            pose_store.save_pose(args.name, joints)
            print(f"Saved pose '{args.name}' with {len(joints)} joints")
            return

    if args.command == "motions":
        if args.motions_command == "list":
            for motion_name in pose_store.list_motions():
                print(motion_name)
            return
        if args.motions_command == "scaffold":
            pose_names = [part.strip() for part in args.poses.split(",") if part.strip()]
            motion = pose_store.scaffold_motion(args.name, pose_names)
            print(f"Saved motion '{motion.name}' with {len(motion.steps)} steps")
            return

    if args.command == "replay":
        if args.replay_command == "pose":
            plan = replay_service.pose_plan(args.name)
            print(plan)
            return
        if args.replay_command == "motion":
            plan = replay_service.motion_plan(args.name)
            print(plan)
            return


if __name__ == "__main__":
    app()
