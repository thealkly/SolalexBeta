"""Unit tests for the hardware adapter modules."""

from __future__ import annotations

import pytest

from solalex.adapters import ADAPTERS
from solalex.adapters.base import AdapterBase, DeviceRecord, HaState


def _dummy_device(adapter_key: str = "generic", role: str = "wr_limit") -> DeviceRecord:
    return DeviceRecord(
        id=1,
        type=adapter_key,
        role=role,
        entity_id=f"number.test_{adapter_key}_limit",
        adapter_key=adapter_key,
    )


class TestRegistry:
    def test_all_three_keys_present(self) -> None:
        assert set(ADAPTERS.keys()) == {"generic", "marstek_venus", "generic_meter"}

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


class TestGenericInverterAdapter:
    def test_build_set_limit_command(self) -> None:
        adapter = ADAPTERS["generic"]
        device = _dummy_device(adapter_key="generic")
        cmd = adapter.build_set_limit_command(device, 150)
        assert cmd.domain == "number"
        assert cmd.service == "set_value"
        assert cmd.service_data["entity_id"] == device.entity_id
        assert cmd.service_data["value"] == 150

    def test_build_set_limit_command_uses_input_number_domain(self) -> None:
        adapter = ADAPTERS["generic"]
        device = DeviceRecord(
            id=1,
            type="generic",
            role="wr_limit",
            entity_id="input_number.trucki_set_target",
            adapter_key="generic",
        )
        cmd = adapter.build_set_limit_command(device, 150)
        assert cmd.domain == "input_number"
        assert cmd.service == "set_value"

    def test_build_set_charge_command_raises(self) -> None:
        adapter = ADAPTERS["generic"]
        device = _dummy_device(adapter_key="generic")
        with pytest.raises(NotImplementedError):
            adapter.build_set_charge_command(device, 300)

    def test_parse_readback_numeric_state(self) -> None:
        adapter = ADAPTERS["generic"]
        state = HaState(entity_id="number.test", state="147")
        assert adapter.parse_readback(state) == 147

    def test_parse_readback_float_state(self) -> None:
        adapter = ADAPTERS["generic"]
        state = HaState(entity_id="number.test", state="52.7")
        assert adapter.parse_readback(state) == 53  # round(), not truncate

    def test_parse_readback_kw_converts_to_watts(self) -> None:
        adapter = ADAPTERS["generic"]
        state = HaState(
            entity_id="number.test",
            state="1.25",
            attributes={"unit_of_measurement": "kW"},
        )
        assert adapter.parse_readback(state) == 1250

    def test_parse_readback_invalid_state_returns_none(self) -> None:
        adapter = ADAPTERS["generic"]
        state = HaState(entity_id="number.test", state="unavailable")
        assert adapter.parse_readback(state) is None

    def test_rate_limit_policy(self) -> None:
        adapter = ADAPTERS["generic"]
        policy = adapter.get_rate_limit_policy()
        assert policy.min_interval_s == 60.0

    def test_readback_timing(self) -> None:
        adapter = ADAPTERS["generic"]
        timing = adapter.get_readback_timing()
        assert timing.timeout_s == 15.0
        assert timing.mode == "sync"

    def test_detect_finds_opendtu_limit_entity(self) -> None:
        adapter = ADAPTERS["generic"]
        states = [
            HaState(
                entity_id="number.opendtu_limit_nonpersistent_absolute",
                state="800",
                attributes={"friendly_name": "OpenDTU Limit", "unit_of_measurement": "W"},
            ),
            HaState(entity_id="sensor.some_power", state="100"),
        ]
        found = adapter.detect(states)
        assert len(found) == 1
        assert found[0].entity_id == "number.opendtu_limit_nonpersistent_absolute"
        assert found[0].suggested_role == "wr_limit"

    def test_detect_finds_trucki_input_number_entity(self) -> None:
        adapter = ADAPTERS["generic"]
        states = [
            HaState(
                entity_id="input_number.t2sgf72a29_t2sgf72a29_set_target",
                state="800",
                attributes={"friendly_name": "Trucki Target", "unit_of_measurement": "W"},
            )
        ]
        found = adapter.detect(states)
        assert len(found) == 1
        assert found[0].adapter_key == "generic"
        assert found[0].suggested_role == "wr_limit"

    def test_limit_range_uses_config_overrides(self) -> None:
        adapter = ADAPTERS["generic"]
        device = DeviceRecord(
            id=1,
            type="generic",
            role="wr_limit",
            entity_id="number.test_limit",
            adapter_key="generic",
            config_json='{"min_limit_w": 5, "max_limit_w": 4200}',
        )
        assert adapter.get_limit_range(device) == (5, 4200)

    def test_drossel_params_use_config_overrides(self) -> None:
        adapter = ADAPTERS["generic"]
        device = DeviceRecord(
            id=1,
            type="generic",
            role="wr_limit",
            entity_id="number.test_limit",
            adapter_key="generic",
            config_json=(
                '{"deadband_w": 12, "min_step_w": 7, '
                '"smoothing_window": 3, "limit_step_clamp_w": 150}'
            ),
        )
        params = adapter.get_drossel_params(device)
        assert params.deadband_w == 12
        assert params.min_step_w == 7
        assert params.smoothing_window == 3
        assert params.limit_step_clamp_w == 150

    def test_invalid_drossel_override_raises(self) -> None:
        adapter = ADAPTERS["generic"]
        device = DeviceRecord(
            id=1,
            type="generic",
            role="wr_limit",
            entity_id="number.test_limit",
            adapter_key="generic",
            config_json='{"smoothing_window": 0}',
        )
        with pytest.raises(ValueError, match="smoothing_window"):
            adapter.get_drossel_params(device)


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


class TestGenericMeterAdapter:
    def test_build_set_limit_command_raises(self) -> None:
        adapter = ADAPTERS["generic_meter"]
        device = _dummy_device(adapter_key="generic_meter", role="grid_meter")
        with pytest.raises(NotImplementedError):
            adapter.build_set_limit_command(device, 100)

    def test_build_set_charge_command_raises(self) -> None:
        adapter = ADAPTERS["generic_meter"]
        device = _dummy_device(adapter_key="generic_meter", role="grid_meter")
        with pytest.raises(NotImplementedError):
            adapter.build_set_charge_command(device, 100)

    def test_parse_readback_w(self) -> None:
        adapter = ADAPTERS["generic_meter"]
        state = HaState(
            entity_id="sensor.shelly_total_power",
            state="1250",
            attributes={"unit_of_measurement": "W"},
        )
        assert adapter.parse_readback(state) == 1250

    def test_parse_readback_kw_converts(self) -> None:
        adapter = ADAPTERS["generic_meter"]
        state = HaState(
            entity_id="sensor.shelly_total_power",
            state="1.25",
            attributes={"unit_of_measurement": "kW"},
        )
        assert adapter.parse_readback(state) == 1250

    def test_detect_finds_esphome_sml_current_load(self) -> None:
        adapter = ADAPTERS["generic_meter"]
        states = [
            HaState(
                entity_id="sensor.00_smart_meter_sml_current_load",
                state="-42",
                attributes={"friendly_name": "SML Current Load", "unit_of_measurement": "W"},
            )
        ]
        found = adapter.detect(states)
        assert len(found) == 1
        assert found[0].adapter_key == "generic_meter"
        assert found[0].suggested_role == "grid_meter"

    def test_detect_ignores_non_power_sensor(self) -> None:
        adapter = ADAPTERS["generic_meter"]
        states = [
            HaState(
                entity_id="sensor.temperature",
                state="21",
                attributes={"unit_of_measurement": "°C"},
            )
        ]
        assert adapter.detect(states) == []
