from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Alert(BaseModel):
    """Alertmanager webhook의 개별 alert."""

    model_config = ConfigDict(populate_by_name=True)

    status: str = ""
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    starts_at: str = Field("", alias="startsAt")
    ends_at: str = Field("", alias="endsAt")
    generator_url: str = Field("", alias="generatorURL")
    fingerprint: str = ""

    @property
    def alertname(self) -> str:
        return self.labels.get("alertname", "unknown")

    @property
    def service(self) -> str:
        return self.labels.get("service", "")


class AlertmanagerPayload(BaseModel):
    """Alertmanager가 webhook으로 보내는 페이로드(version 4)."""

    model_config = ConfigDict(populate_by_name=True)

    status: str = ""
    receiver: str = ""
    group_labels: dict[str, str] = Field(default_factory=dict, alias="groupLabels")
    common_labels: dict[str, str] = Field(default_factory=dict, alias="commonLabels")
    common_annotations: dict[str, str] = Field(default_factory=dict, alias="commonAnnotations")
    external_url: str = Field("", alias="externalURL")
    alerts: list[Alert] = Field(default_factory=list)
