# HVAC COP & Thermal Performance Advisor

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/v/release/pegaverzum/hvac_cop_advisor?style=for-the-badge)](https://github.com/pegaverzum/hvac_cop_advisor/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Hassfest Validation](https://img.shields.io/github/actions/workflow/status/pegaverzum/hvac_cop_advisor/validate.yml?label=Hassfest&style=for-the-badge)](https://github.com/pegaverzum/hvac_cop_advisor/actions)

Production-grade Home Assistant custom integration that transforms any connected air conditioner or heat pump (monitored via a smart plug or energy meter) into an intelligent, thermodynamically-aware thermal power and efficiency station.

Calculates real-time **COP** (heating), **EER** (cooling), delivered **Thermal Power (Watts)**, **Compressor Modulation (%)**, accumulated **kWh**, and provides an automated **Smart Pre-heating Advisor** based on upcoming weather forecasts.

---

> [!NOTE]
> **Languages / Nyelvek:**
> - [English Documentation](#english-documentation)
> - [Magyar Dokumentáció](#magyar-dokumentáció)

---

<a name="english-documentation"></a>
## English Documentation

### Key Features
- **Dynamic COP & EER Calculation:** Real-time thermodynamic interpolation factoring in indoor/outdoor temperature difference ($\Delta T$) and inverter compressor modulation.
- **Partial Load Efficiency Optimization:** Thermodynamic curve modeling compressor efficiency peaks (+8% to +12% efficiency boost around 30–65% partial load) and overdrive penalties.
- **Thermal Power & Energy Delivered:** Instantaneous output in Watts ($W$) and accumulated energy in $kWh$ (`total_increasing` compatible with Home Assistant Energy Dashboard).
- **Daily Average COP (SCOP):** Automatically tracked and calculated over each calendar day ($SCOP_{daily} = \Delta E_{thermal} / \Delta E_{electric}$).
- **Smart Pre-Heating Weather Advisor:** Utilizes modern `weather.get_forecasts` to detect sharp temperature drops ($\ge 6^\circ\text{C}$ or freezing conditions), recommending pre-charging the building's thermal mass while outdoor temperatures and COP are high.
- **Fully Configurable via UI:** Config Flow and live Options Flow for parameter tuning without YAML or restarts.
- **100% Bilingual:** English and Hungarian out of the box.

---

### Thermodynamic Models & Formulas

#### 1. Temperature-Dependent Base Efficiency
- **Heating Mode:**
  Reference nominal point: $+7^\circ\text{C}$ outdoor, $+20^\circ\text{C}$ indoor ($\Delta T_{ref} = 13^\circ\text{C}$).
  $$\Delta T = T_{indoor} - T_{outdoor}$$
  $$COP_{temp} = \text{clamp}\left(COP_{nominal} - k_{cop} \cdot (\Delta T - 13),\; 1.1,\; 6.0\right)$$
  *(Default $k_{cop} = 0.065$)*

- **Cooling Mode:**
  Reference nominal point: $+35^\circ\text{C}$ outdoor, $+27^\circ\text{C}$ indoor.
  $$EER_{temp} = \text{clamp}\left(EER_{nominal} - k_{eer} \cdot (T_{outdoor} - 35),\; 1.5,\; 6.5\right)$$
  *(Default $k_{eer} = 0.08$)*

#### 2. Compressor Inverter Modulation & Partial-Load Multiplier
Nominal electrical power:
$$P_{elec\_nom} = \frac{\text{Nominal Capacity (kW)} \times 1000}{COP_{nominal}\text{ (or }EER_{nominal}\text{)}}$$

Modulation rate:
$$\text{Modulation \%} = \min\left(150,\; \max\left(0,\; \frac{P_{measured\_watts}}{P_{elec\_nom}} \times 100\right)\right)$$

Efficiency multiplier:
- **Optimal partial load (30% to 65% modulation):**
  $$Multiplier = 1.0 + 0.12 \cdot \left(1.0 - \left\vert{}\frac{\text{Modulation} - 47.5}{17.5}\right\vert{}\right)$$
- **Nominal load (80% to 100%):** $Multiplier \approx 1.00$
- **Overdrive (>100% to 150%):** Efficiency penalty down to $-20\%$

Effective COP:
$$COP_{effective} = COP_{temp} \times Multiplier$$

#### 3. Instantaneous Thermal Power & Energy Integration
$$P_{thermal} = P_{measured\_watts} \times COP_{effective}\quad(W)$$
*(Output is 0 W when climate is off, in fan/dry mode, or power is below standby threshold, default 15 W).*

Energy accumulation uses Riemann trapezoidal summation with state restoration across Home Assistant restarts (`RestoreEntity`).

---

### Entities Provided

| Entity | Type | Name | Unit | Class |
| :--- | :--- | :--- | :--- | :--- |
| `sensor.<device>_cop_eer` | Sensor | Instantaneous COP / EER | - | measurement |
| `sensor.<device>_thermal_power` | Sensor | Thermal Output Power | `W` | power |
| `sensor.<device>_modulation` | Sensor | Compressor Modulation | `%` | measurement |
| `sensor.<device>_cumulative_electric_energy` | Sensor | Total Electric Energy Consumed | `kWh` | energy (`total_increasing`) |
| `sensor.<device>_cumulative_thermal_energy` | Sensor | Total Thermal Energy Delivered | `kWh` | energy (`total_increasing`) |
| `sensor.<device>_daily_cop` | Sensor | Daily Average COP | - | measurement |
| `binary_sensor.<device>_heat_recommended` | Binary Sensor | Heating Recommended | - | heat |
| `binary_sensor.<device>_preheating_advisor` | Binary Sensor | Pre-Heating Recommended | - | - |

---

### Installation via HACS

1. Open **Home Assistant** -> **HACS** -> **Integrations**.
2. Click the three dots in the top right corner -> **Custom repositories**.
3. Add the repository URL: `https://github.com/pegaverzum/hvac_cop_advisor`
4. Category: **Integration**.
5. Click **Add**, find **HVAC COP & Thermal Advisor**, and click **Download**.
6. Restart Home Assistant.
7. In **Settings** -> **Devices & Services**, click **Add Integration** and search for **HVAC COP & Thermal Advisor**.

---

<a name="magyar-dokumentáció"></a>
## Magyar Dokumentáció

### Főbb Jellemzők
- **Valós idejű COP és EER számítás:** Termodinamikai interpoláció a belső és külső hőmérséklet-különbség ($\Delta T$) és az inverteres kompresszor moduláció alapján.
- **Részterhelési Hatásfok Korrekció:** +8% – +12% COP növekedés 30–65%-os részterhelésnél (a túlméretezett hőcserélő felület miatt), és büntetés 100% feletti túlterhelésnél.
- **Leadott Termikus Teljesítmény és Energia:** Pillanatnyi hőteljesítmény Wattban ($W$) és összesített termikus energia $kWh$-ban (`total_increasing`, Home Assistant Energy Dashboard kompatibilis).
- **Napi Átlagos Hatásfok (SCOP):** Napi összesített termikus és villamos energia aránya, automatikus éjféli nullázással.
- **Okos Előfűtési Időjárás Tanácsadó:** A modern `weather.get_forecasts` szolgáltatással figyeli az elkövetkező 6–12 óra lehűléseit ($\ge 6^\circ\text{C}$ esés vagy fagy), és javasolja az épület előfűtését, amíg kint enyhe az idő és magas a COP.
- **UI-n keresztül konfigurálható:** Teljes Config Flow és utólagos Options Flow felület.
- **Teljes magyar nyelvű támogatás.**

---

### Telepítés HACS-on keresztül

1. Nyisd meg a Home Assistantban a **HACS** -> **Integrációk** menüt.
2. Kattints a jobb felső sarokban található három pontra -> **Egyéni tárolók (Custom repositories)**.
3. Add meg a tároló URL-jét: `https://github.com/pegaverzum/hvac_cop_advisor`
4. Kategória: **Integráció (Integration)**.
5. Kattints a **Hozzáadás** gombra, keresd meg a **HVAC COP & Thermal Advisor** elemet, majd válaszd a **Letöltés** lehetőséget.
6. Indítsd újra a Home Assistantot.
7. A **Beállítások** -> **Eszközök és Szolgáltatások** -> **Integráció hozzáadása** menüben keresd meg a **HVAC COP & Thermal Advisor** elemet.

---

### Home Assistant Energia Műszerfal (Energy Dashboard) Beállítása

1. Lépj a **Beállítások** -> **Műszerfalak** -> **Energia** menüpontba.
2. A **Villamosenergia-hálózat** vagy **Egyedi fogyasztók** szekcióban add hozzá a klíma okoskonnektorát vagy a generált `sensor.<eszköz>_cumulative_electric_energy` entitást.
3. A termikus energiamérő (`sensor.<eszköz>_cumulative_thermal_energy`) pontosan mutatja az otthonodba bevitt fűtési/hűtési hőmennyiséget.

---

### Licenc
MIT License — Nyílt forráskódú, szabadon felhasználható és módosítható.
