from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.orm.base import Base


class ReviewRuleConfig(Base):
    """Singleton-style configuration for AI review focus areas."""

    __tablename__ = "review_rule_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    focus_security: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    focus_performance: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    focus_strict_typing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    focus_logic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
