"""Unit tests for the hardware adapter modules."""

from __future__ import annotations

import pytest

from solalex.adapters import ADAPTERS
from solalex.adapters.base import AdapterBase, DeviceRecord, HaState


def _dummy_device(adapter_key: str = "hoymiles", role: str = "wr_limit") -> DeviceRecord:
    return DeviceRecord(
        id=1,
        type=adapter_key,
        role=role,
        entity_id=f"number.test_{adapter_key}_limit",
        adapter_key=adapter_key,
    )


class TestRegistry:
    def test_all_three_keys_present(self) -> None:
        assert set(ADAPTERS.keys()) == {"hoymiles", "marstek_venus", "shelly_3em"}

    def test_all_adapters_are_adapter_base_instances(self) -> None:
        for key, adapter in ADAPTERS.items():
            assert isinstance(adapter, AdapterBase), f"{key} is not an AdapterBase instance"

    def test_all_adapters_implement_required_methods(self) -> None:
        required = [
            "detect",
            "build_set_limit_command",
            "build_set_charge_command",
            "parse_readback",
            "get_rate_limit_policy",
            "get_readback_timing",
        ]
        for key, adapter in ADAPTERS.items():
            for method in required:
                assert hasattr(adapter, method), f"{key}.{method} is missing"


class TestHoymilesAdapter:
    def test_build_set_limit_command(self) -> None:
        adapter = ADAPTERS["hoymiles"]
        device = _dummy_device(adapter_key="hoymiles")
        cmd = adapter.build_set_limit_command(device, 150)
        assert cmd.domain == "number"
        assert cmd.service == "set_value"
        assert cmd.service_data["entity_id"] == device.entity_id
        assert cmd.service_data["value"] == 150

    def test_build_set_charge_command_raises(self) -> None:
        adapter = ADAPTERS["hoymiles"]
        device = _dummy_device(adapter_key="hoymiles")
        with pytest.raises(NotImplementedError):
            adapter.build_set_charge_command(device, 300)

    def test_parse_readback_numeric_state(self) -> None:
        adapter = ADAPTERS["hoymiles"]
        state = HaState(entity_id="number.test", state="147")
        assert adapter.parse_readback(state) == 147

    def test_parse_readback_float_state(self) -> None:
        adapter = ADAPTERS["hoymiles"]
        state = HaState(entity_id="number.test", state="52.7")
        assert adapter.parse_readback(state) == 52

    def test_parse_readback_invalid_state_returns_none(self) -> None:
        adapter = ADAPTERS["hoymiles"]
        state = HaState(entity_id="number.test", state="unavailable")
        assert adapter.parse_readback(state) is None

    def test_rate_limit_policy(self) -> None:
        adapter = ADAPTERS["hoymiles"]
        policy = adapter.get_rate_limit_policy()
        assert policy.min_interval_s == 60.0

    def test_readback_timing(self) -> None:
        adapter = ADAPTERS["hoymiles"]
        timing = adapter.get_readback_timing()
        assert timing.timeout_s == 15.0
        assert timing.mode == "sync"

    def test_detect_finds_opendtu_limit_entity(self) -> None:
        adapter = ADAPTERS["hoymiles"]
        states = [
            HaState(
                entity_id="number.opendtu_limit_nonpersistent_absolute",
                state="800",
                attributes={"friendly_name": "OpenDTU Limit"},
            ),
            HaState(entity_id="sensor.some_power", state="100"),
        ]
        found = adapter.detect(states)
        assert len(found) == 1
        assert found[0].entity_id == "number.opendtu_limit_nonpersistent_absolute"
        assert found[0].suggested_role == "wr_limit"


class TestMarstekVenusAdapter:
    def test_build_set_charge_command(self) -> None:
        adapter = ADAPTERS["marstek_venus"]
        device = DeviceRecord(
            id=1,
            type="marstek_venus",
            role="wr_charge",
            entity_id="number.marstek_charge_power",
            adapter_key="marstek_venus",
        )
        cmd = adapter.build_set_charge_command(device, 300)
        assert cmd.domain == "number"
        assert cmd.service == "set_value"
        assert cmd.service_data["value"] == 300

    def test_build_set_limit_command_raises(self) -> None:
        adapter = ADAPTERS["marstek_venus"]
        device = _dummy_device(adapter_key="marstek_venus", role="wr_charge")
        with pytest.raises(NotImplementedError):
            adapter.build_set_limit_command(device, 100)

    def test_readback_timing(self) -> None:
        adapter = ADAPTERS["marstek_venus"]
        timing = adapter.get_readback_timing()
        assert timing.timeout_s == 30.0


class TestShelly3EmAdapter:
    def test_build_set_limit_command_raises(self) -> None:
        adapter = ADAPTERS["shelly_3em"]
        device = _dummy_device(adapter_key="shelly_3em", role="grid_meter")
        with pytest.raises(NotImplementedError):
            adapter.build_set_limit_command(device, 100)

    def test_build_set_charge_command_raises(self) -> None:
        adapter = ADAPTERS["shelly_3em"]
        device = _dummy_device(adapter_key="shelly_3em", role="grid_meter")
        with pytest.raises(NotImplementedError):
            adapter.build_set_charge_command(device, 100)

    def test_parse_readback_w(self) -> None:
        adapter = ADAPTERS["shelly_3em"]
        state = HaState(
            entity_id="sensor.shelly_total_power",
            state="1250",
            attributes={"unit_of_measurement": "W"},
        )
        assert adapter.parse_readback(state) == 1250

    def test_parse_readback_kw_converts(self) -> None:
        adapter = ADAPTERS["shelly_3em"]
        state = HaState(
            entity_id="sensor.shelly_total_power",
            state="1.25",
            attributes={"unit_of_measurement": "kW"},
        )
        assert adapter.parse_readback(state) == 1250
