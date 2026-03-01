# Smart Recuperator

[![Home Assistant](https://img.shields.io/badge/Home_Assistant-Package-41BDF5.svg?style=for-the-badge&logo=homeassistant)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

**Intelligent climate automation** for Blauberg / Siku wall-mounted recuperators.  
Coordinates your recuperators with heating, humidity sensors, weather data, and more — all from a single YAML package.

> Works with the [Siku Integration](https://github.com/hmn/siku-integration) and pairs perfectly with the [Blauberg Recuperator Card](https://github.com/skeep83/blauberg-recuperator-card).

## 🧠 What it does

Transform your recuperators from simple fans into an **intelligent ventilation system** that reacts to your home's climate in real-time.

## ✨ Automation Modules

| Module | Description | Trigger |
|--------|-------------|---------|
| 💧 **Humidity Control** | Auto-boost when humidity is high, restore when normal | Room humidity > 65% |
| 🔥 **Heating Sync** | Reduce ventilation to save heat when boiler runs | Boiler ON + outdoor < 5°C |
| 🌡️ **Dew Point Protection** | Prevent condensation on windows | ΔT to dew point < 3°C |
| 🌙 **Night Mode** | Quiet operation during sleep hours | 22:00 — 07:00 |
| 🔄 **Filter Alerts** | Notification when filter needs replacement | Filter life < 14 days |
| 🌤️ **Weather Adaptation** | Minimize intake during rain, storm, or extreme heat | Weather conditions |

Every module can be **independently enabled/disabled** via UI toggle switches.

## 📊 Template Sensors Created

| Sensor | Description |
|--------|-------------|
| `sensor.smart_recup_outdoor_temp` | Outdoor temperature from weather |
| `sensor.smart_recup_outdoor_humidity` | Outdoor humidity from weather |
| `sensor.smart_recup_dewpoint_*` | Dew point per room (Magnus formula) |
| `sensor.smart_recup_filter_*` | Filter life remaining in days |
| `sensor.smart_recup_status_*` | Smart status: Норма / Осушение / Ночной / Эконом |

## 📦 Installation

### 1. Copy the package

Download `smart_recuperator.yaml` and place it in your HA `config/packages/` directory:

```bash
config/
  packages/
    smart_recuperator.yaml
```

### 2. Enable packages in configuration.yaml

```yaml
homeassistant:
  packages:
    smart_recuperator: !include packages/smart_recuperator.yaml
```

### 3. Restart Home Assistant

After restart, go to **Settings → Devices → Helpers** to find the new toggle switches and threshold controls.

## ⚙️ Configurable Thresholds

All thresholds are adjustable via **Settings → Helpers** — no YAML editing needed:

| Helper | Default | Description |
|--------|---------|-------------|
| Humidity Boost (%) | 65 | Trigger boost above this level |
| Humidity Stop (%) | 55 | Stop boost below this level |
| Night Speed (%) | 25 | Fan speed during night mode |
| Heating Min Speed (%) | 25 | Min speed when boiler is running |
| Cold Threshold (°C) | 5 | "Cold outside" definition |
| Hot Threshold (°C) | 30 | "Hot outside" definition |
| Filter Warning (days) | 14 | Alert when filter life below |
| Night Start | 22:00 | Night mode start time |
| Night End | 07:00 | Night mode end time |

## 🏠 Supported Devices

Built and tested with 3 Blauberg VENTO recuperators via [Siku Integration](https://github.com/hmn/siku-integration):

| Room | IP | Fan Entity |
|------|----|-----------| 
| Спальня Амели | 192.168.1.41 | `fan.siku_blauberg_fan_192_168_1_41` |
| Мастер Спальня | 192.168.1.49 | `fan.siku_blauberg_fan_192_168_1_49` |
| Спальня Пацанов | 192.168.1.50 | `fan.siku_blauberg_fan_192_168_1_50` |

> **Customization:** Edit entity IDs in `smart_recuperator.yaml` to match your setup.

## 🔗 Related

- [Siku Integration](https://github.com/hmn/siku-integration) — Required HA integration for Siku/Blauberg recuperators
- [Blauberg Recuperator Card](https://github.com/skeep83/blauberg-recuperator-card) — Neumorphic card for visual control
- [Altal Heater Card](https://github.com/skeep83/altal_heater_card) — Matching card for Altal heat pumps

## 📄 License

MIT © 2026
