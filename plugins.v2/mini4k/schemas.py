# -*- coding: utf-8 -*-
from typing import Optional

from pydantic import BaseModel, Field


class SearchMini4kToolInput(BaseModel):
    """Mini4k search agent tool input."""

    explanation: str = Field(
        ...,
        description="Explanation of why Mini4k should be searched.",
    )
    keyword: str = Field(
        ...,
        description="Movie search keyword, Chinese title, English title, or IMDb-style text.",
    )
    page: Optional[int] = Field(
        default=0,
        description="Mini4k search page number, starting from 0.",
    )
    limit: Optional[int] = Field(
        default=5,
        description="Maximum number of torrent results to show.",
    )


class LoginMini4kToolInput(BaseModel):
    """Mini4k login agent tool input."""

    explanation: str = Field(
        ...,
        description="Explanation of why Mini4k login or cookie refresh is needed.",
    )

