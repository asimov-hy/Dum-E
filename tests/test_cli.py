from dum_e.main import build_parser, parse_joint_values


def test_parser_accepts_motor_set_id() -> None:
    parser = build_parser()

    args = parser.parse_args(["motors", "set-id", "--name", "gripper", "--to-id", "9"])

    assert args.command == "motors"
    assert args.motors_command == "set-id"
    assert args.name == "gripper"
    assert args.to_id == 9


def test_parse_joint_values() -> None:
    joints = parse_joint_values("0, 0.5, -1")

    assert joints == [0.0, 0.5, -1.0]
