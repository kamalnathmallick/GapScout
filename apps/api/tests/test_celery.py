from app.tasks import ping


def test_ping_task_returns_pong() -> None:
    result = ping.apply()

    assert result.successful()
    assert result.get() == "pong"
