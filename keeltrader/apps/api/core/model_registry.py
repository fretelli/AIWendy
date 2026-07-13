"""Register every SQLAlchemy model for API, worker, and CLI entrypoints."""

from sqlalchemy.orm import configure_mappers


def register_domain_models() -> None:
    import domain.analysis.models  # noqa: F401
    import domain.agent_platform.models  # noqa: F401
    import domain.coach.models  # noqa: F401
    import domain.exchange.models  # noqa: F401
    import domain.file.models  # noqa: F401
    import domain.journal.models  # noqa: F401
    import domain.project.models  # noqa: F401
    import domain.research_cloud.models  # noqa: F401
    import domain.rpg.models  # noqa: F401
    import domain.user.models  # noqa: F401

    configure_mappers()
