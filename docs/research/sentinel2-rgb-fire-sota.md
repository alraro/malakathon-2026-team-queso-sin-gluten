# Wildfire delineation & active-fire detection from *rendered* Sentinel-2 RGB composites

**State of the art, and what survives when the input is an 8-bit JPEG.**

Research notes for Malackathon 2026 / Indra Espacio challenge. Compiled 2026-10-15.

Every factual claim below is tagged:

| Tag | Meaning |
|---|---|
| **[PRIMARY]** | Traced to the evalscript source, the paper, the agency spec, the model card or the dataset card. Link given. |
| **[MEASURED]** | My own measurement on the three JPEGs in `data/`. Not literature. Reproducible from the stated formula. |
| **[INFERRED]** | A derivation or deduction I made from primary material. Reasoning shown so you can disagree. |
| **[UNVERIFIED]** | Could not reach a primary source. Treat as a lead, not a fact. Collected in §8. |

---

## 0. What to build — the verdict up front

### Basic objective (burned-area delineation + perimeter)

> **Backbone: NBR computed *inside* the SWIR composite, thresholded scene-adaptively (multi-Otsu on the NBR histogram), cleaned morphologically, vectorised with `find_contours` + Douglas–Peucker.**

The reason this is the right call, compressed:

1. The SWIR composite is **[PRIMARY]** `[2.5*B12, 2.5*B8A, 2.5*B04]` — a plain linear gain, no tone curve ([`swir-rgb/script.js`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/swir-rgb/script.js)).
2. So `NBR ≈ (SWIR_G − SWIR_R)/(SWIR_G + SWIR_R)` — **the gain 2.5 cancels exactly in the normalised difference**, and both operands live in the *same* file, so there is no cross-image calibration problem and no gamma to undo. This is the one index that is essentially *lossless* on these inputs (§2.4).
3. **[MEASURED]** It works: burn scars sit at NBR ≈ −0.16/−0.21 median, vegetation at +0.35/+0.42, with a clean margin (§4.6 table).
4. Thresholds must be **derived per scene from the histogram**, never hard-coded — judges run unseen scenes, and §2.2 shows even Key & Benson tell you to retune per scene.

Then: **reject false positives with a second, independent opinion from the True Color composite** — specifically the smoke/cloud discriminator in §4.3, which is the highest-scoring part of the rubric and the part most teams will miss.

### Advanced objective (active fire at acquisition time)

> **If the scene ships a `Wildfires` composite: decode it. Its fire colours are a hard 4-level classification of `B12 + B11 > {2.0, 1.5, 1.25, 1.0}` baked into the pixel. Else: fall back to `B12`-saturation ∧ `B12/B8A ≥ 1.4` ∧ `B12 ≥ 0.15` (two of Murphy's three tests) from the SWIR composite, and say in the UI that confidence is lower.**

The reason, compressed:

1. The Copernicus Browser `Wildfires` layer is Pierre Markuse's **QuickFire v1.0.0**, and I have the source. It is *not* a pretty picture — it is a thresholded detector whose output is painted into the RGB (§1.3). Decoding it is a legitimate, defensible shortcut, and you can cite the evalscript for it.
2. **[MEASURED]** Its hotspot pixels form exactly the two colour families the script predicts (saturated-yellow top tier, orange/red lower tiers) — §1.4. The semantics check out.
3. **[MEASURED]** The killer argument: `B12 + B11 > 1.0` **cannot be reproduced from the SWIR composite**, because `B11` is in neither composite. A naive `B12`-render threshold over-detects by **13×** against the QuickFire mask (§1.5). The `Wildfires` layer is carrying real information you cannot otherwise obtain — use it when present.
4. **[MEASURED]** Containment self-check for free: 91–99 % of QuickFire hotspots fall inside your `NBR < 0` scar mask (§5.3). That is a validation figure you can put on a slide.

### What not to spend the 48 h on

Learned segmentation from scratch, any geospatial foundation model, anything needing a pre-fire image, and real-world area figures stated without a declared pixel size. All explained in §7.

---

## 1. The exact Sentinel Hub visualization recipes

### 1.1 Which browser produced these files

The filenames (`2026-08-08-00_00_2026-08-08-23_59_Sentinel-2_L2A_SWIR.jpg`) and the presence of a layer literally named **`Wildfires`** point to the **Copernicus Browser** (`dataspace.copernicus.eu/browser`) rather than the legacy EO Browser. A wildfire visualization layer was added to the Copernicus Browser as a *default* option for Sentinel-2 in August 2026, based on Markuse's script **[UNVERIFIED — reported by secondary press coverage, e.g. [eu-space / businessstory summary](https://www.businessstory.org/2026/08/07/europes-free-satellite-service-just-made-it-easier-to-track-wildfires/); I could not find the CDSE documentation page for the layer itself]**.

This matters because the custom-scripts repo ships **two variants** of QuickFire with *different constants* — one for each browser (§1.3). You must pick the right one.

**[MEASURED]** File inventory:

| Scene | Date | Size (px) | Products | Notes |
|---|---|---|---|---|
| `madrid-avila` | 2026-07-26 | 9930 × 6141 | True color, SWIR | > 2500 px ⇒ "High-res print" export, **not georeferenced** |
| `huelva` | 2026-08-08 | 2500 × 1546 | True color, SWIR, Wildfires | exactly at the 2500 px cap |
| `guadalajara` | 2026-07-21 | 2500 × 1546 | True color, SWIR, Wildfires | exactly at the 2500 px cap |

JPEG metadata contains only JFIF density and (inconsistently) an ICC profile. **No EXIF, no GeoTIFF tags, no bbox, no CRS.** Confirmed by reading every file.

### 1.2 True Color and SWIR

**[PRIMARY]** The canonical custom-scripts definitions:

```js
// sentinel-2/true_color/script.js
let gain = 2.5;
return [sample.B04 * gain, sample.B03 * gain, sample.B02 * gain, sample.dataMask];
```
([source](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/true_color/script.js))

```js
// sentinel-2/swir-rgb/script.js
input: ["B12","B8A","B04","dataMask"]
return [2.5 * sample.B12, 2.5 * sample.B8A, 2.5 * sample.B04, sample.dataMask];
```
([source](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/swir-rgb/script.js))

So the brief's belief is confirmed: **SWIR = B12 → R, B8A → G, B04 → B**, gain 2.5, linear, hard-clipped at reflectance 0.4.

Some Sentinel Hub composites instead use `HighlightCompressVisualizer(0.0, 0.4)` — e.g. [`false-color-urban-rgb`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/false-color-urban-rgb/script.js) on `[B12, B11, B04]`. **[INFERRED]** Below its knee this is *the same thing as gain 2.5*: see §1.6.

#### The complication I measured, and you must handle

**[MEASURED]** `B04` appears in **both** composites — as `TC_R` (True Color red) and as `SWIR_B` (SWIR blue). If both layers used the same transfer function these two channels would be numerically identical. They are not.

- Correlation is high, confirming they are the same band: `corr(SWIR_B, TC_R)` = 0.952 / 0.930 / 0.913 for huelva / guadalajara / madrid-avila. (Against `TC_G` and `TC_B` the correlation is lower — 0.87/0.66 for huelva — so the pairing is right.)
- But a power law fits the relation with scene-independent exponent:

| Scene | fit | RMSE |
|---|---|---|
| huelva | `TC_R = 0.927 · SWIR_B^0.391` | 4.9 DN |
| guadalajara | `TC_R = 0.974 · SWIR_B^0.450` | 9.3 DN |
| madrid-avila | `TC_R = 0.990 · SWIR_B^0.473` | 11.0 DN |

(normalised to [0,1]; fitted on `0.02 < x,y < 0.97` to avoid clipping.)

i.e. **`SWIR_B ≈ TC_R^2.1…2.6`** — the two composites differ by a tone curve of power ≈ **2.2**, consistently across all three scenes. A linear fit needs a +80…+100 DN intercept and fits worse, so this is not a gain difference.

**[INFERRED] Which one carries the gamma.** Take the median pixel. If True Color is the gamma-encoded one: `TC_R`med = 162/255 = 0.635 ⇒ linear = 0.635^2.2 = 0.368 ⇒ `B04` = 0.147. And independently from SWIR as plain gain 2.5: `SWIR_B`med = 94/255 = 0.369 ⇒ `B04` = 0.147. **The two agree.** If instead SWIR carried the gamma and True Color were linear, both routes give `B04` ≈ 0.26 — implausibly high for red reflectance over dry Mediterranean scrub and burn scar. So:

> **True Color carries an output gamma of ≈ 1/2.2. The SWIR composite is linear gain 2.5.**

Labelled **[INFERRED]** because I could not retrieve the Copernicus Browser's actual built-in layer definitions (§8). The *measurement* of the ≈2.2 relation is solid; the attribution of it to True Color is a deduction.

#### Inversion recipe (the arithmetic you asked for)

```
# SWIR composite  -> linear reflectance.  Exact up to clipping.
B12 = (SWIR_R / 255) / 2.5
B8A = (SWIR_G / 255) / 2.5
B04 = (SWIR_B / 255) / 2.5
#   valid only while the channel is < 255; saturates at reflectance 0.4

# True Color -> linear reflectance.  Gamma is INFERRED, not documented.
B04 = (TC_R / 255) ** 2.2 / 2.5
B03 = (TC_G / 255) ** 2.2 / 2.5
B02 = (TC_B / 255) ** 2.2 / 2.5
```

**Invertibility verdict per channel:**

| Channel | Band | Transfer | Invertible? |
|---|---|---|---|
| `SWIR_R` | B12 | linear × 2.5, clipped | **Yes, exactly** — below 255 |
| `SWIR_G` | B8A | linear × 2.5, clipped | **Yes, exactly** — below 255 |
| `SWIR_B` | B04 | linear × 2.5, clipped | **Yes, exactly** — below 255 |
| `TC_R/G/B` | B04/B03/B02 | gain 2.5 **+ gamma ≈1/2.2** | Yes, but the exponent is **[INFERRED]** |
| — | **B11** | **absent from both composites** | **No** |

Everything above reflectance **0.4** is destroyed by clipping in every channel. For fire work this is not a side note — it is the main event, because **fire pixels are exactly the pixels that clip** (§1.5).

### 1.3 The `Wildfires` layer — what it actually encodes

**[PRIMARY]** It is **QuickFire V1.0.0 by Pierre Markuse**, CC BY 4.0, published on his blog September 2022, shipped in the Sentinel Hub custom-scripts repo as [`sentinel-2/markuse_fire`](https://github.com/sentinel-hub/custom-scripts/tree/main/sentinel-2/markuse_fire) with a [README](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/markuse_fire/README.md) and **two variants**:

- [`script.js`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/markuse_fire/script.js) — EO Browser
- [`cdse.js`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/markuse_fire/cdse.js) — **Copernicus Browser** ← the relevant one

**This is the single highest-value finding in this document.** The render is **not a continuous ramp**. It is a base visualization with a **hard 4-tier classification painted over it**:

```js
const hsThreshold = [2.0, 1.5, 1.25, 1.0];   // thresholds on (B12 + B11)
const boost = 1.2;                            // cdse.js  (script.js uses 1)

if (hotspot) {
  if ((!cloudAvoidance) || (!isCloud(sample) && (sample.B02 < 0.8))) {
    if ((B12+B11) > 2.00) return [0.60*B12 + Viz[0], 0.60*B11 + Viz[1], Viz[2], dataMask];
    if ((B12+B11) > 1.50) return [0.60*B12 + Viz[0], 0.24*B11 + Viz[1], Viz[2], dataMask];
    if ((B12+B11) > 1.25) return [0.60*B12 + Viz[0], 0.12*B11 + Viz[1], Viz[2], dataMask];
    if ((B12+B11) > 1.00) return [0.60*B12 + Viz[0], 0.00        + Viz[1], Viz[2], dataMask];
  }
}
```

Read this carefully, because the semantics are precise:

- **The detection criterion is `B12 + B11 > 1.0`** — the sum of the two SWIR reflectances exceeding 1.0 (i.e. physically impossible for a merely sunlit surface; it requires thermal emission at SWIR wavelengths). This is the fire test.
- **The blue channel is never touched** by the hotspot branch. So fire pixels are *always* `R` and/or `G` boosted with `B` left at the base value ⇒ **high `R − B`** is the decodable signature.
- **Tier → colour**: the green boost coefficient steps `0.60 → 0.24 → 0.12 → 0.00` while red stays at `0.60·B12`. So the hottest tier is **yellow/near-white**, and successively cooler tiers go **orange → red-orange → pure-red**. It is a 4-level ordinal *intensity* classification, not a binary mask.
- **Within a tier there is still a continuous component** (`0.60·B12`, `0.60·B11`), so brightness inside a tier varies. It is "hard classification of *which* tier, continuous *within* tier".
- **Cloud avoidance is ON by default** (`cloudAvoidance = 1`). In `cdse.js` it uses a Browser-local cloud test because CDSE has no `CLP` band:
  ```js
  function isCloud(samples) {
      const NGDR  = index(samples.B03, samples.B04);          // (B03-B04)/(B03+B04)
      const bRatio = (samples.B03 - 0.175) / (0.39 - 0.175);
      return bRatio > 1 || (bRatio > 0 && NGDR > 0);
  }
  ```
  plus `B02 < 0.8`. **This is a documented failure mode you must state in your report: a fire under or beside bright cloud is suppressed in the render.** The script's own comment says "do try to turn off cloudAvoidance if results aren't as expected."
- **`showBurnscars = 0`** by default — so the `Wildfires` render does **not** contain a burn-scar overlay. Do not try to read scars out of it; use NBR from the SWIR composite instead.

The base visualization under the hotspots (`cdse.js`):

```js
const brightness = 1.40, offset = -0.007, saturation = 1.10;
const sMin = 0.15, sMax = 0.99;
const manualCorrection = [0.04, 0.00, -0.05];

naturalColorsCC = [sqrt(1.4*B04 - 0.007), sqrt(1.4*B03 - 0.007), sqrt(1.4*B02 - 0.007)]
URBAN           = [sqrt(1.4*1.2*B12 - 0.007), sqrt(1.4*1.4*B11 - 0.007), sqrt(1.4*B04 - 0.007)]
SWIR            = [sqrt(1.4*B12 - 0.007), sqrt(1.4*B8A - 0.007), sqrt(1.4*B04 - 0.007)]

Viz = 0.10*URBAN + 0.10*SWIR + 0.90*naturalColorsCC   // layerBlend(.., 10, 10, 90)
Viz = satEnh(Viz, 1.10)                                // v -> 1.10*v - 0.10*mean(Viz)
Viz = (Viz - 0.15) / (0.99 - 0.15)  +  manualCorrection
```

The EO Browser variant differs materially — `boost = 1`, `offset = -0.000`, `brightness = 1.00`, `sMin = 0.01`, `manualCorrection = [0,0,0]`, and a different blend `layerBlend(URBAN, naturalColors, naturalColorsCC, 10, 40, 50)`. **If a judge hands you an EO Browser export, the base colours shift.** Your decoder must key on the *hotspot signature* (`R` high, `R − B` large), which is robust to the base, and not on absolute RGB values.

### 1.4 **[MEASURED]** The Wildfires semantics check out on the real data

Selecting candidate hotspots as `R > 200 ∧ (R − B) > 120`:

| Scene | hot px | % of scene | mean WF RGB | mean SWIR RGB at those px | mean TC RGB |
|---|---|---|---|---|---|
| huelva | 8 629 | 0.223 % | (244, 168, 91) | (248, 166, 132) | (174, 165, 150) |
| guadalajara | 572 | 0.015 % | (234, 172, 94) | (246, 145, 98) | (159, 158, 148) |

Quantising those hotspot pixels to a 16-level colour cube reveals **exactly the two families QuickFire predicts**:

- `(240, 240, 48…128)` — **yellow/near-white**: the `B12+B11 > 2.0` top tier, where green gets the full `0.60·B11` boost.
- `(240, 160, 96)`, `(240, 144, 80)`, `(208, 128, 64)` — **orange → red**: the `1.0 < B12+B11 ≤ 1.5` tiers, where green gets 0.24/0.12/0.00.

This is independent confirmation that the render is the tier structure in the source, and it gives you a concrete decode rule.

**Forward-model cross-check.** Using the published `cdse.js` constants I predicted `WF_R` and `WF_B` from True Color + SWIR (both are functions of `B12`, `B04`, `B02` only — see §2.5), on non-hotspot, non-clipped pixels:

| Scene | `WF_R` corr | `WF_B` corr |
|---|---|---|
| huelva | 0.977 | 0.981 |
| guadalajara | 0.973 | 0.938 |

Correlations of 0.94–0.98 against the published formula confirm the script identity. There is a large residual *bias* (+40…+56 DN) because I fed it reflectances derived with the wrong tone curve — which is precisely how I discovered the gamma in §1.2. **Do not read the bias as a refutation; read it as the tone-curve discovery.**

### 1.5 **[MEASURED]** Why the Wildfires layer is irreplaceable

The QuickFire criterion is `B12 + B11 > 1.0`. **`B11` is in neither composite.** The best SWIR-composite-only proxy is a threshold on rendered `B12`. Comparing them:

| Scene | QuickFire hotspots | `SWIR_R > 0.90` proxy | over-detection |
|---|---|---|---|
| huelva | 8 658 px | 110 331 px | **12.7 ×** |
| guadalajara | 577 px | 25 772 px | **44.7 ×** |

Recall is fine (99.9 % / 94.5 % of QuickFire hotspots are inside the proxy) — but precision collapses, because bright bare soil and dry stubble also drive `B12` high. **The `B11` term is what rejects hot soil.** This is the same insight the operational literature reports: the AFD-S2 multi-criteria method adds a `B12/B11` ratio criterion specifically "to avoid false alarms from hot soil" ([Hu et al. 2021, *Int. J. Appl. Earth Obs. Geoinf.*](https://www.sciencedirect.com/science/article/pii/S0303243421000544)) **[PRIMARY for the existence of the criterion; the per-biome numeric thresholds are behind the paywall — [UNVERIFIED]]**.

**Actionable consequence:** when `Wildfires` is present, decode it. When it is absent (as in `madrid-avila`), you *must* degrade gracefully and lower the confidence you report — do not pretend the SWIR-only mask is equivalent.

### 1.6 **[INFERRED]** `HighlightCompressVisualizer`, derived exactly

The Sentinel Hub / CDSE docs ([Utilities](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Evalscript/Utilities.html), [Utility Functions](https://docs.sentinel-hub.com/api/latest/evalscript/functions/)) describe this as "a piecewise linear function which compresses highlights" and give example values but **no formula**. The documented facts: `minValue → 0`; `maxValue → ≈0.9259`; `2·maxValue − minValue → 1`; the breakpoint is at 0.92; and `0.376 = minValue + 0.92·(maxValue − minValue)`.

That over-determines the function. With `t = (x − min)/(max − min)`:

```
hc(t) = t                                        for t ≤ 0.92
hc(t) = 0.92 + (t − 0.92) · (0.08 / 1.08)        for 0.92 < t < 2
hc(t) = 1                                        for t ≥ 2
```

Check at `t = 1`: `0.92 + 0.08 · 0.074074 = 0.925926` = the documented **0.9259**. ✓

**[MEASURED]** I evaluated this against all seven documented examples for `new HighlightCompressVisualizer(0.1, 0.4)` and it reproduces **every one exactly**: `process(0)=0`, `process(0.1)=0`, `process(0.25)=0.5`, `process(0.376)=0.92`, `process(0.4)=0.9259`, `process(0.7)=1`, `process(1.1)=1`.

**Why you care:** with `minVal = 0, maxVal = 0.4`, `hc` is *identical to gain 2.5* for all reflectance below 0.368, and only soft-rolls-off above. So a `HighlightCompressVisualizer(0, 0.4)` layer and a `gain = 2.5` layer are interchangeable over 92 % of the range — and neither of them explains the ≈2.2 gamma I measured in §1.2. The gamma must come from the Browser layer's styling, outside the evalscript. **[UNVERIFIED]** — §8.

---

## 2. Canonical spectral indices, and which survive

### 2.1 Band availability — the table everything else follows from

| Band | λ (nm) | Native res. | Available from these JPEGs? |
|---|---|---|---|
| B02 blue | 490 | 10 m | ✅ `TC_B` (gamma) |
| B03 green | 560 | 10 m | ✅ `TC_G` (gamma) |
| B04 red | 665 | 10 m | ✅ **twice** — `TC_R` (gamma) and `SWIR_B` (linear) |
| B05–B07 red-edge | 705–783 | 20 m | ❌ |
| B08 NIR | 842 | 10 m | ❌ — but **B8A is a valid stand-in** |
| B8A narrow NIR | 865 | 20 m | ✅ `SWIR_G` (linear) |
| B09 water vapour | 945 | 60 m | ❌ |
| B10 cirrus | 1375 | 60 m | ❌ (also absent from L2A entirely) |
| **B11 SWIR-1** | **1610** | **20 m** | ❌ **— the single most consequential gap** |
| B12 SWIR-2 | 2190 | 20 m | ✅ `SWIR_R` (linear) |

Band wavelengths/resolutions per the [CDSE Sentinel-2 L2A documentation](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html) **[PRIMARY]**.

**B8A for B08:** 865 nm vs 842 nm, both on the NIR plateau. Substituting B8A into NBR is standard practice — note Sentinel Hub's own [`swir-rgb`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/swir-rgb/script.js) uses B8A where the [composites page](https://custom-scripts.sentinel-hub.com/sentinel-2/composites/) describes the SWIR composite as `RGB(12,8,4)`, and [BAIS2](#24-burned-area-indices) is defined on B8A. Treat the swap as sound; mention it in your report for honesty.

### 2.2 NBR and dNBR — and the trap

**[PRIMARY]** NBR, per Sentinel Hub's [`nbr/script.js`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/nbr/script.js), citing [IndexDataBase si-single 53](https://www.indexdatabase.de/db/si-single.php?sensor_id=96&rsindex_id=53):

```
NBR = (B08 - B12) / (B08 + B12)          # general form: (NIR - SWIR) / (NIR + SWIR)
dNBR = NBR_prefire - NBR_postfire
```

The owning document is **Key, C.H. & Benson, N.C. (2006), "Landscape Assessment (LA)", in FIREMON, USDA Forest Service RMRS-GTR-164-CD** — [full chapter PDF](https://www.fs.usda.gov/rm/pubs/rmrs_gtr164/rmrs_gtr164_13_land_assess.pdf) **[PRIMARY]**.

**Severity class breaks.** The widely-quoted table is the **EFFIS adaptation** of Key & Benson, on dNBR × 1000 ([EFFIS Fire Severity](https://forest-fire.emergency.copernicus.eu/about-effis/technical-background/fire-severity)) **[PRIMARY for EFFIS using them; [UNVERIFIED] that these exact breaks appear in the original chapter]**:

| dNBR × 1000 | Class |
|---|---|
| < 100 | Unburned / regrowth |
| 100 – 270 | Low severity |
| 270 – 440 | Moderate-low |
| 440 – 660 | Moderate-high |
| ≥ 660 | High severity |

**The trap, and read this twice:** Key & Benson themselves prescribe *scene-specific* threshold setting, not fixed cutoffs. The chapter tells you to colour dNBR from the top down until patches form, expects the high-severity lower threshold to land "within a range of about +600 to +750", the extreme upper limit "within a range of about +1,000 to +1,300", and states thresholds "may need to be shifted up or down, depending on relative scene conditions indicated by unburned background."

> **Therefore: quoting fixed dNBR severity numbers at the judges is *literature-incorrect*, not just risky. The owning document says to adapt per scene. This is your justification for scene-adaptive thresholding, and it is a strong one — cite it.**

**And the bigger trap: `dNBR` is not computable at all here.** It needs a **pre-fire acquisition**. You have one date per scene. Everything built on dNBR — all the severity classes above, Sentinel Hub's [`burned_area`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/burned_area/script.js) multitemporal script (which hard-codes `dnbr < 0.27` / `< 0.66` breaks) — is **out of reach**. See §7.

You are restricted to **single-date NBR**, which has no absolute calibration. Hence: histogram-adaptive thresholds, and report *relative* severity at most.

### 2.3 **[MEASURED]** Single-date NBR on the actual scenes

Computed as `(SWIR_G − SWIR_R)/(SWIR_G + SWIR_R)` straight off the SWIR JPEG:

| Scene | p1 | p5 | p25 | p50 | p75 | p99 |
|---|---|---|---|---|---|---|
| huelva | −0.219 | −0.085 | 0.029 | 0.102 | 0.191 | 0.430 |
| guadalajara | −0.310 | −0.197 | 0.067 | 0.171 | 0.323 | 0.633 |
| madrid-avila | −0.361 | −0.079 | 0.034 | 0.112 | 0.221 | 0.648 |

Fraction of scene below a candidate threshold:

| Scene | NBR<−0.10 | NBR<0.00 | NBR<+0.10 | NBR<+0.20 |
|---|---|---|---|---|
| huelva | 4.3 % | 16.2 % | 49.4 % | 77.0 % |
| guadalajara | 8.2 % | 13.1 % | 33.0 % | 55.9 % |
| madrid-avila | 4.2 % | 15.3 % | 46.1 % | 71.4 % |

**Two things to take away.** (1) The useful operating range is roughly `NBR < −0.05 … 0.00`; `NBR < +0.10` is far too permissive (one third to one half of the scene). (2) The distributions differ enough between scenes that a single hard cutoff would behave very differently on each — direct empirical support for the multi-Otsu / adaptive approach, and a line you can put in the report.

### 2.4 Burned-area indices — availability verdict for each

| Index | Definition | Source | Computable here? |
|---|---|---|---|
| **NBR** | `(B8A − B12)/(B8A + B12)` | [Key & Benson 2006](https://www.fs.usda.gov/rm/pubs/rmrs_gtr164/rmrs_gtr164_13_land_assess.pdf); [SH script](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/nbr/script.js) | ✅ **Yes — exactly, gain-invariant, single file.** The backbone. |
| **dNBR** | `NBR_pre − NBR_post` | same | ❌ no pre-fire image |
| **NBR2** | `(B11 − B12)/(B11 + B12)` | attributed to Lutes et al. 2006 / Key & Benson 1999 — **[UNVERIFIED]**, found no USGS page owning it | ❌ **needs B11** |
| **BAIS2** | `(1 − √(B06·B07·B8A / B04)) · ((B12 − B8A)/√(B12 + B8A) + 1)` | [Filipponi 2018](https://www.researchgate.net/publication/323964124_BAIS2_Burned_Area_Index_for_Sentinel-2), DOI [10.3390/ecrs-2-05177](https://doi.org/10.3390/ecrs-2-05177); formula as implemented in [SH `bais2/script.js`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/bais2/script.js) | ❌ **needs B06, B07** |
| **BAI** | `1 / ((0.1 − Red)² + (0.06 − NIR)²)` | Chuvieco et al. 2002 (some sources credit Martín 1998) — **[UNVERIFIED]** attribution | ⚠️ **Yes, but** — needs Red + NIR in consistent units; mixes the gamma'd TC with the linear SWIR, so it is calibration-fragile. Not worth it. |
| **MIRBI** | `10·B12 − 9.8·B11 + 2` | Trigg & Flasse 2001 — **[UNVERIFIED]**, could not reach the original; sources disagree on 2000 vs 2001 and one prints 0.98 for 9.8 | ❌ **needs B11** |
| **NDVI** | `(B08 − B04)/(B08 + B04)` | standard | ⚠️ **Proxy only** — `(B8A − B04)/(B8A + B04)` using `SWIR_G` and `SWIR_B`, both linear, both in one file ⇒ **gain-invariant and actually usable**. Good news; see below. |

**The BAIS2 note worth knowing [PRIMARY]**, from the [SH BAIS2 README](https://github.com/sentinel-hub/custom-scripts/blob/main/sentinel-2/bais2/README.md): *"The range of values for the BAIS2 is -1 to 1 for burn scars, and 1 - 6 for active fires."* So BAIS2 separates scar from active fire in one index — elegant, and **unavailable to you** because of B06/B07. Mention it in the report as the thing you would use with real multiband input; it shows you know the field.

Filipponi reported a BAIS2 threshold of **0.865** for Sicily, July 2017 **[UNVERIFIED — this number reaches me only through secondary citation; the primary PDF (sciforum, MDPI) returned HTTP 403]**.

**The NDVI-proxy good news [INFERRED]:** because `SWIR_G` = `2.5·B8A` and `SWIR_B` = `2.5·B04` both live in the *same linear* render, `(SWIR_G − SWIR_B)/(SWIR_G + SWIR_B)` is a **genuine, gain-invariant NDVI** (with B8A for B08). So you get **two** independent gain-invariant indices out of the single SWIR JPEG: NBR (R vs G) and NDVI (G vs B). Burned surface is low in *both*; water is low-NDVI but *high*-NBR; cloud is near-zero NBR. Combining them is cheap and discriminating.

### 2.5 Partial B11 recovery — I tried it, it does not work. Don't repeat this.

The `Wildfires` render's **green** channel is the only place `B11` appears (via `URBAN[1] = sqrt(1.4·1.4·B11 − 0.007)`, weight 0.10). `WF_R` and `WF_B` depend only on `B12`, `B04`, `B02`. So in principle `B11` is recoverable: solve the `satEnh`+`stretch` chain for `Viz[1]`, subtract the known `B8A` and `B03` contributions, and invert the sqrt.

**[MEASURED] It collapses numerically.** Recovered `B11` pinned to the `−offset/(1.4·1.4)` = 0.00357 floor at both p1 and p50, with `corr(B11_rec, B12)` = 0.26 / 0.23 — i.e. noise. Two compounding reasons:

1. The `B11` term enters with weight **0.10** *inside a square root*. One DN of 8-bit `WF_G` quantisation is amplified by ≈10 in sqrt-space before squaring. The channel simply does not carry enough bits.
2. It is only solvable if the tone curves of all three renders are known exactly — and §1.2 shows one of them is **[INFERRED]**. Residual tone-curve error swamps a 0.10-weighted term.

Plus JPEG chroma subsampling degrades `WF_G` further, and the whole derivation is void inside hotspots (where the branch returns something else).

> **Verdict: `B11` is not recoverable in any useful form. Treat it as absent. The information you want from `B11` is already available, pre-digested and far more robustly, as the QuickFire tier colours — use those instead.**

This is the clean, honest resolution: don't invert for `B11`, read the classification the script already did for you.

### 2.6 Active-fire algorithms, and what transfers

**[PRIMARY]** Exact thresholds as reimplemented in [de Almeida Pereira et al., *Active Fire Detection in Landsat-8 Imagery: a Large-Scale Dataset and a Deep-Learning Study* (arXiv:2101.03409)](https://arxiv.org/html/2101.03409v2). Landsat-8 bands 5/6/7 = NIR / SWIR-1 / SWIR-2 ≈ Sentinel-2 **B8A / B11 / B12**. `ρᵢ` = reflectance, `Rᵢⱼ = ρᵢ/ρⱼ`.

**Murphy et al. (2016)** — non-contextual, bands 5,6,7. *(HOTMAP: Murphy, de Souza Filho, Wright, Sabatino & Pabon, Remote Sens. Environ. 177:78–88, [DOI 10.1016/j.rse.2016.02.027](https://doi.org/10.1016/j.rse.2016.02.027); reported ≈80 % hot-pixel detection at <10 % false-alarm rate)*

| Condition | S2 equivalent | Computable? |
|---|---|---|
| `R76 ≥ 1.4` | `B12/B11 ≥ 1.4` | ❌ needs B11 |
| `R75 ≥ 1.4` | `B12/B8A ≥ 1.4` | ✅ **yes** |
| `ρ7 ≥ 0.15` | `B12 ≥ 0.15` | ✅ **yes** |
| potential: `R65 ≥ 2 ∧ ρ6 ≥ 0.5` | `B11/B8A ≥ 2 ∧ B11 ≥ 0.5` | ❌ needs B11 |
| potential: band 6 or 7 **saturated** | `B11` or `B12` saturated | ⚠️ **partially** — `SWIR_R = 255` *is* a saturation flag |
| 3×3 dilation of unambiguous into potential | — | ✅ trivially |

> **So 2 of Murphy's 3 unambiguous conditions are directly computable, plus the saturation cue, plus the spatial growth step.** That is your fallback detector for scenes with no `Wildfires` layer. Call it "Murphy-partial" in the code and be explicit in the report that the `B12/B11` test is omitted — honesty here will score better than a silent approximation.

**Schroeder et al. (2016)** — bands 1–7, contextual on a 61×61 window:
- Unambiguous: `(R75 > 2.5 ∧ ρ7 − ρ5 > 0.3 ∧ ρ7 > 0.5)` **or** `(ρ6 > 0.8 ∧ ρ1 < 0.2 ∧ (ρ5 > 0.4 ∨ ρ7 < 0.1))`
- Contextual: `R75 > 1.8 ∧ ρ7 − ρ5 > 0.17 ∧ R76 > 1.6 ∧ R75 > μ(R75) + max(3σ(R75), 0.8) ∧ ρ7 > μ(ρ7) + max(3σ(ρ7), 0.08)`, with fire and water pixels excluded from μ, σ
- Water test: `ρ4 > ρ5 ∧ ρ5 > ρ6 ∧ ρ6 > ρ7 ∧ ρ1 − ρ7 < 0.2 ∧ (ρ3 > ρ2 ∨ ρ1 > ρ2 > ρ3 > ρ4)`

The **first unambiguous clause is fully computable from the SWIR composite** (`B12/B8A > 2.5 ∧ B12 − B8A > 0.3 ∧ B12 > 0.5`) and the **contextual μ+3σ idea is the genuinely valuable, transferable part** — a local-background anomaly test that is intrinsically scene-adaptive, needs no absolute calibration, and generalises to unseen scenes. **Steal this pattern even if you can't run the full algorithm.** It also happens to be the best answer to "how do you avoid per-scene hand tuning".

**Kumar & Roy (2018)** — bands 2–7; unambiguous `ρ4 ≤ 0.53·ρ7 − 0.214`, neighbour growth `ρ4 ≤ 0.35·ρ6 − 0.044`, potential `ρ4 ≤ 0.53·ρ7 − 0.125` or `ρ6 ≤ 1.08·ρ7 − 0.048`, neighbourhood grown 5×5→61×61 until ≥25 % usable. The `ρ4`/`ρ7` (= B04/B12) clauses **are computable** — and `B04` and `B12` are both in the linear SWIR render, so they are calibration-clean. Worth trying as a cross-check.

*Note: the brief mentioned "Kato & Enomoto"; the arXiv paper's third algorithm is Kumar & Roy (2018), not Kato. I did not locate a Kato & Enomoto active-fire algorithm — **[UNVERIFIED]**, possibly a different work or a misattribution.*

**Other Sentinel-2-specific work:**
- **AFD-S2** — [Hu et al. 2021](https://www.sciencedirect.com/science/article/pii/S0303243421000544), multi-criteria biome-specific, thresholds from a 3σ prediction interval of an OLS fit per biome over 11 M observations (Jun–Sep 2019, 14 regions). Uses **B04, B11, B12**. Commission error 0.14, omission 0.04; validation largely by visual inspection as ground truth was unavailable. Per-biome numbers paywalled — **[UNVERIFIED]**.
- **Thermal Anomaly Level** — forms normalised differences of B11 with B8A and B12 with B11; and a Borneo study used a `B12/B11/B8A` thermal anomaly index with a lenient 0.01 threshold ([Tandfonline 2025](https://www.tandfonline.com/doi/full/10.1080/15481603.2025.2539551)). Both need B11.
- **Fire Boundary script [PRIMARY]** — [`fire_boundary/script.js`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/fire_boundary/script.js): `8.5·(B12 − B11)/(B12 + B11 + 0.25)`, Putra & Ramdani. Needs B11. ❌
- **EO Browser wildfires-theme Burned Area Visualization [PRIMARY]** — [`burned_area_ms/script.js`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/burned_area_ms/script.js), by Monja Šebela. A fully explicit operational rule:
  ```js
  INDEX = (B11 - B12)/(B11 + B12) + B08
  // NOT burned (shown in natural colour) if:
  INDEX > 0.1 || B02 > 0.1 || B11 < 0.1 || NDVI > 0.3 || NDWI > 0.1
  // else -> burned, painted red
  ```
  Needs B11 and B08, so ❌ — **but its *structure* is highly reusable**: a burn index gated by three independent false-positive rejectors (bright-blue ⇒ cloud, low-SWIR1 ⇒ water/shadow, high-NDVI ⇒ vegetation, high-NDWI ⇒ water). **That gating pattern is what the rubric's "false positive reduction" criterion is asking for, and you can build the same shape from `B02`(TC), NDVI-proxy and NBR.** Note the README says the index threshold is `>0.15 for S2L1C` while the code says `0.1` — a **[PRIMARY]** internal inconsistency; prefer the code.

**Relation to VIIRS/MODIS thermal products.** These are the reference truth in the literature: Sen2Fire's labels come from MODIS **MOD14A1 V6.1**; EFFIS uses MODIS/VIIRS active-fire detections as ancillary input to its burned-area mapping. Note the resolution mismatch — VIIRS active fire is **375 m** nominal, MODIS 1 km, against Sentinel-2's 20 m. So they validate *presence and rough location*, never per-pixel extent. Use them as in §5.1, not as a pixel-level target.

---

## 3. Learned segmentation — state of the art, and the 3-channel filter

### 3.1 Datasets

| Dataset | Content | Bands | Labels | Licence / access |
|---|---|---|---|---|
| **California S2 Active-Fire Segmentation v1.0.0** ⭐ | 2 148 pairs, 512×512, 25 California wildfires (841 with fire, 1 307 fire-free) | **3 rendered 8-bit channels, B12-B11-B8A, 20 m** | SWIR hot-target rule "motivated by HOTMAP"; 0/1/255 (255 = invalid, *not* cloud); 233/432 test chips analyst-reviewed, 89.7 % chip agreement | **CC BY 4.0** (code MIT), [Zenodo 10.5281/zenodo.22713948](https://doi.org/10.5281/zenodo.22713948), [arXiv:2609.16199](https://arxiv.org/pdf/2609.16199) |
| **Landsat-8 ActiveFire** | Part 1: 146 214 patches 256×256 (~192 GB) from 8 194 scenes; Part 2: 9 044 manually annotated (~12 GB) | 10 Landsat-8 bands, 16-bit TIFF | Murphy / Schroeder / Kumar-Roy masks + manual | arXiv CC BY-NC-ND 4.0; dataset licence not stated on the paper — check the repo. [arXiv:2101.03409](https://arxiv.org/pdf/2101.03409) |
| **Sen2Fire** | 2 466 patches 512×512, 4 regions NSW Australia, 2019-20 season | 12 S2 bands (cirrus dropped) + 1 Sentinel-5P aerosol layer | MODIS **MOD14A1 V6.1** | **CC BY 4.0**, 6.3 GB (`Sen2Fire.zip`) + baseline code — [Zenodo record 10881058](https://zenodo.org/records/10881058); IGARSS 2024, [arXiv:2403.17884](https://arxiv.org/abs/2403.17884) |
| **HLS Burn Scars** | ~800 labelled chips 512×512, continental US | 6 HLS bands | 0 = unburned, 1 = burned, −1 = nodata/cloud | [HuggingFace `ibm-nasa-geospatial/hls_burn_scars`](https://huggingface.co/datasets/ibm-nasa-geospatial/hls_burn_scars) |
| **Copernicus EMS rapid mapping** | Per-activation burnt-area delineation & grading vectors | vector | expert-delineated | [mapping.emergency.copernicus.eu](https://mapping.emergency.copernicus.eu/) — see §5.2 |

> ⭐ **The California dataset is the single most relevant artefact in the whole literature for your situation**, and almost nobody would guess it exists. It is **three rendered 8-bit channels** — exactly your input modality, not float reflectance. Caveat: its channel order is **B12-B11-B8A**, while your SWIR composite is **B12-B8A-B04**. So the weights are not directly transferable, but the *recipe* (ResNet-34 U-Net on a 3×8-bit SWIR composite) is proven and directly reproducible.

### 3.2 Architectures and published numbers

| Model | Task / dataset | Reported | Source |
|---|---|---|---|
| ResNet-34 U-Net | active fire, California S2 (3×8-bit) | **IoU 0.837**, P 0.897, R 0.926 (thr 0.99); val IoU 0.876 | [arXiv:2609.16199](https://arxiv.org/pdf/2609.16199) |
| U-Net (10 bands), voting ensemble | active fire, Landsat-8 auto masks | P 92.9, R 95.5, **IoU 89.0**, F1 94.2 | [arXiv:2101.03409](https://arxiv.org/html/2101.03409v2) |
| U-Net-Light (**3 bands**), voting | active fire, Landsat-8 *manual* annotations | P 87.2, R 92.4, **IoU 81.4**, F1 89.7 | same |
| original threshold algorithms | same manual annotations | best F1 ≈ 90 | same |
| Prithvi-EO-2.0-300M + UNetDecoder | HLS burn scars | **burn IoU 87.52**, mIoU 93.00 | [HF model card](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-300M-BurnScars) |

**The number that should decide your strategy:** on the Landsat-8 manual annotations, a **3-band U-Net-Light reaches IoU 81.4 / F1 89.7**, and **the hand-written threshold algorithms reach F1 ≈ 90 on the same data.** The classical algorithms match the deep models. With 48 h, no labels for your scenes, and only rendered RGB, **the classical path is not the compromise — it is the competitive choice**, and you can cite this to justify it.

### 3.3 Ready-to-use weights that accept 3-channel 8-bit RGB

| Model | Input expectation | Usable in 48 h? |
|---|---|---|
| ResNet-34 U-Net (California S2) | **3 × 8-bit, B12-B11-B8A** | ✅ closest match by far — but **channel order differs** from your composite; weights would need either a re-train or a channel remap you cannot validate. Realistically: reproduce the *method*, not the weights. |
| U-Net-Light 3c (Landsat-8 ActiveFire) | 3 Landsat bands (NIR/SWIR1/SWIR2 = B8A/B11/B12 equivalent) | ⚠️ needs B11; you'd substitute B04 for B11 — unvalidated |
| **Prithvi-EO-2.0-300M-BurnScars** | **6 bands: Blue, Green, Red, Narrow NIR, SWIR-1, SWIR-2** | ⚠️ **You have 5 of the 6.** `TC_B`→Blue, `TC_G`→Green, `TC_R`/`SWIR_B`→Red, `SWIR_G`→Narrow NIR, `SWIR_R`→SWIR-2. **Only SWIR-1 (B11) is missing.** But: 300 M-parameter ViT, TerraTorch + config, HLS-specific normalisation statistics, and you'd have to fabricate B11. Document it as the "with more time" path; do not attempt it. |
| SAM / SAM2 | 3-channel 8-bit RGB, natively | ✅ **the only FM that takes your input with zero surgery** — §4.5 |
| Clay, DOFA, SatMAE, other geospatial FMs | 6–13 bands, sensor-specific embeddings | ❌ channel surgery + fine-tuning; out of scope |

> **The non-obvious alignment worth writing down:** Prithvi-BurnScars wants exactly Blue/Green/Red/NarrowNIR/SWIR1/SWIR2, and True Color + SWIR between them supply **five of those six** — the composites were, by accident, chosen almost perfectly for it. The one missing band is B11, the same band that blocks NBR2, MIRBI, the Fire Boundary script and Murphy's first test. **Every single gap in this document is the same gap.** If a judge asks "what one extra input would most improve this?", the answer is **B11**, and you can say why in one sentence.

### 3.4 Prompted / zero-shot segmentation

- **SAM for remote sensing** — [Osco et al. 2023, *Int. J. Appl. Earth Obs. Geoinf.*](https://www.sciencedirect.com/science/article/pii/S1569843223003643) ([arXiv:2306.16623](https://arxiv.org/pdf/2306.16623)) **[PRIMARY]**: tested point, box and text prompts across UAV/airborne/satellite. Finding: **box prompts outperform point prompts for geometrically well-defined, larger objects**; the best prompt type depends on object and resolution.
- **Zero-shot burned-area with SAM** exists and is the closest published analogue: composites built from **NBR, NBR2 and NDVI** fed to SAM as its input representation under a zero-shot configuration — *not* index-derived point/box seeds. **[UNVERIFIED]** — surfaced only via search snippet; I could not open the primary record. Worth 10 minutes of searching if you pursue this.
- **SAM2 with box prompts in EO** is validated in adjacent domains: a detector localises objects and its boxes prompt SAM2 for zero-shot masks ([SAR ship instance segmentation, arXiv:2604.17920](https://arxiv.org/html/2604.17920v1)); and for *flame* segmentation, "strategic bounding box prompting significantly enhances segmentation performance" ([arXiv:2510.21782](https://arxiv.org/html/2510.21782)).
- **[UNVERIFIED]** I found **no** published SAM2 burned-area evaluation seeded by spectral-index points/boxes. If you do it, it is genuinely novel — which is worth points under "originality" — but it is unproven, so keep it as a *refinement layer on top of* the NBR mask, never as the primary path.

**Realistic 48 h use:** threshold NBR → connected components → emit each component's bounding box → SAM2 box prompt → union of returned masks → compare IoU against the threshold mask. If it improves boundary adherence, keep it; if not, you have a measured ablation to report, which is itself a good slide. Box prompts, per Osco et al., not points.

---

## 4. Classical CV on rendered composites — the backbone

### 4.1 The 6-channel stack

Stack True Color + SWIR into one 6-channel array (they are co-registered, same instant, same grid — stated in the challenge brief and confirmed by the 0.95 `SWIR_B`/`TC_R` correlation in §1.2). Derived features worth adding, all **gain-invariant**:

```
NBR_proxy   = (SWIR_G - SWIR_R) / (SWIR_G + SWIR_R)     # B8A vs B12   -> burn
NDVI_proxy  = (SWIR_G - SWIR_B) / (SWIR_G + SWIR_B)     # B8A vs B04   -> vegetation
D           = z(mean(TC)) - z(mean(SWIR))               # the smoke discriminator, §4.3
```

`NBR_proxy` and `NDVI_proxy` are both computed *within* the linear SWIR render, so the 2.5 gain cancels and no tone-curve knowledge is needed. **Prefer these to anything that mixes the two files.**

### 4.2 **[MEASURED]** Per-class signatures from the real scenes

Values are rendered channels in [0,1]. Classes defined by simple rules (stated below the table) — these are *my* operational definitions for measurement, not ground truth.

**huelva (2026-08-08)**

| class | % scene | TC_R | TC_G | TC_B | SW_R | SW_G | SW_B | NBR | `D` |
|---|---|---|---|---|---|---|---|---|---|
| fire (QuickFire hotspot) | 0.22 | 0.682 | 0.645 | 0.587 | **0.972** | 0.650 | 0.519 | **−0.298** | −0.48 |
| burn scar | 2.61 | 0.537 | 0.496 | 0.452 | 0.541 | 0.389 | 0.255 | **−0.158** | +0.06 |
| vegetation | 8.06 | 0.546 | 0.552 | 0.500 | 0.299 | 0.640 | 0.281 | +0.352 | −0.06 |
| bright-both (cloud) | 2.22 | 0.818 | 0.737 | 0.642 | 0.881 | 0.934 | 0.795 | **+0.028** | −0.42 |
| smoke | 1.12 | 0.684 | 0.700 | 0.697 | 0.330 | 0.585 | 0.466 | +0.279 | **+2.15** |
| dark-both (water/shadow) | 1.16 | 0.434 | 0.442 | 0.367 | 0.239 | 0.419 | 0.165 | +0.302 | −0.35 |

**guadalajara (2026-07-21)**

| class | % scene | TC_R | TC_G | TC_B | SW_R | SW_G | SW_B | NBR | `D` |
|---|---|---|---|---|---|---|---|---|---|
| fire (QuickFire hotspot) | 0.015 | 0.625 | 0.620 | 0.582 | **0.964** | 0.568 | 0.385 | **−0.262** | −0.01 |
| burn scar | 2.88 | 0.444 | 0.399 | 0.330 | 0.408 | 0.269 | 0.172 | **−0.205** | +0.63 |
| vegetation | 28.08 | 0.409 | 0.423 | 0.259 | 0.279 | 0.706 | 0.160 | +0.420 | −0.33 |
| bright-both (cloud) | 2.04 | 0.816 | 0.750 | 0.662 | 0.799 | 0.921 | 0.770 | **+0.073** | −0.52 |
| smoke | 0.30 | 0.670 | 0.689 | 0.689 | 0.315 | 0.505 | 0.426 | +0.259 | **+2.07** |
| dark-both (water/shadow) | 0.47 | 0.242 | 0.277 | 0.132 | 0.122 | 0.331 | 0.057 | +0.436 | −0.31 |

*Class rules: fire = QuickFire decode (`WF_R>200/255 ∧ WF_R−WF_B>120/255`); burn scar = `NBR<−0.05 ∧ TC brightness < p40`; vegetation = `NBR>0.30`; cloud = `TC>p97 ∧ SWIR>p90`; smoke = `TC>p92 ∧ SWIR<p55`; water/shadow = `TC<p3 ∧ SWIR<p3`.*

**What to read out of this:**

- **Fire is `SWIR_R` ≈ 0.97 — saturated.** Fire in the SWIR composite is *saturated red*. That is the whole signature, and it is why clipping at reflectance 0.4 matters so much.
- **Burn scar is red-dominant and dark** (`SW_R` > `SW_G` > `SW_B`): a brown/maroon in the SWIR composite. **Vegetation is green-dominant** (`SW_G` ≈ 0.64–0.71 ≫ `SW_R`). The separation is in `SW_R` vs `SW_G` — which *is* NBR. Direct empirical confirmation that NBR-from-the-SWIR-render is the correct backbone.
- ⚠️ **Cloud sits at NBR ≈ +0.03 … +0.07.** A naive `NBR < 0.10` threshold **will swallow clouds**, and §2.3 shows that threshold also takes a third to half the scene. **This is the classic false positive and the most likely way to lose points.** You must gate clouds out separately.
- **Water/shadow is dark in both but NBR-*high*** (+0.30 / +0.44). So NBR does *not* confuse water with burn — a useful negative result. Water gets caught by low brightness, not by NBR.

### 4.3 ⭐ **[MEASURED]** Smoke vs cloud, with no cirrus band and no Sen2Cor SCL

**The physics [PRIMARY-ish].** Smoke aerosol scattering falls off with wavelength (Ångström relation, AOD ∝ λ^−α, α ≈ 1–2 for fine smoke), so SWIR at 1.6–2.2 µm passes through smoke that is opaque in the visible. Supporting statements: SWIR bands "generally provide good active fire discrimination when the fire is unobscured by optically thick smoke" ([Schroeder et al., Landsat-8 reflectance-based active fire algorithm](https://www.tandfonline.com/doi/full/10.1080/17538947.2017.1391341)); "the presence of smoke results in low transmittance" in visible and thermal data, motivating SWIR as a substitute input ([Landsat-8 thermal disaggregation on a wildfire scene](https://www.researchgate.net/publication/322735302_Disaggregation_of_Landsat-8_Thermal_Data_Using_Guided_SWIR_Imagery_on_the_Scene_of_a_Wildfire)). **Caveat, stated in the sources: penetration is seen in many but not all situations, and optically thick smoke still blocks SWIR.** I could not find a primary source tabulating AOD by Sentinel-2 band — **[UNVERIFIED]** for the quantitative wavelength dependence; the qualitative direction is well supported.

**The exploit, and I measured it.** Because the two composites are co-registered and simultaneous, smoke makes them **disagree**, and nothing else does. Define

```
D = z(mean(TC_RGB)) - z(mean(SWIR_RGB))        # z = per-scene standardisation
```

| class | median `D` (huelva) | median `D` (guadalajara) |
|---|---|---|
| **smoke** | **+2.148** | **+2.067** |
| burn scar | +0.059 | +0.630 |
| vegetation | −0.057 | −0.334 |
| fire | −0.478 | −0.008 |
| **cloud** | **−0.417** | **−0.523** |
| water/shadow | −0.354 | −0.312 |

> **Smoke is the only class with large positive `D` (≈ +2.1, consistent across both scenes). Cloud — bright in the visible *and* bright in SWIR — sits at ≈ −0.5. So `D` separates smoke from cloud cleanly, which is exactly the thing the cirrus band and the Sen2Cor scene classification would normally be needed for.** A threshold around `D > +1.0` is a defensible smoke mask, and it is scene-adaptive by construction because `D` is built from z-scores.

This is the highest-leverage finding in §4: the rubric explicitly grades cloud-and-smoke false-positive rejection, and this gives you a *measured, physically-motivated, two-source* discriminator rather than a colour heuristic. It also exists only because you have two co-registered composites — which turns the apparent handicap of the input format into an advantage. Say that in the report.

Note the asymmetry that makes it work: **cloud is bright in both; smoke is bright in visible only; burn scar is dark in both but NBR-negative; water is dark in both but NBR-positive.** Four classes, two brightness channels plus NBR, fully separable.

### 4.4 Segmentation and perimeter toolchain

All of this is in `scikit-image` / `scipy`, which are **not currently installed** (§6).

- **Thresholding:** `skimage.filters.threshold_multiotsu` on the NBR histogram — Otsu minimises intra-class variance, derives the cutoff from the scene, no magic constant. Multi-Otsu with 3 classes maps naturally to {unburned, burned, strongly burned}. This is the single most important choice for generalising to unseen scenes.
- **Colour-space decision regions:** work in HSV or CIE-Lab rather than raw RGB. **[MEASURED]** In the SWIR composite, scar pixels sit at V ≈ 0.53–0.69, S ≈ 0.39–0.50 versus scene medians V ≈ 0.64–0.69, S ≈ 0.47–0.59 — i.e. **HSV alone separates scar only weakly**; the discrimination is in hue/channel-ratio, which is what NBR already captures. **Conclusion: prefer index space to colour space here.** Use Lab only for the final visual rendering.
- **Unsupervised clustering:** GMM or k-means on the 6-channel stack (+ NBR, NDVI_proxy, `D`) is a reasonable automation story — it needs no thresholds at all. Risk: cluster-to-class assignment is unstable across scenes, so you must label clusters by a rule (e.g. "the cluster with lowest mean NBR is burn"), not by index.
- **Mahalanobis distance** to a sampled class is a good "confidence" output for the UI, and the rubric asks for confidence levels.
- **Region growing / watershed / felzenszwalb:** use for the *active-fire* step, mirroring Murphy's and Schroeder's own 3×3 / 61×61 neighbourhood growth — seed on unambiguous detections, grow into "potential" pixels. This is the literature-sanctioned way to get coherent fire fronts rather than speckle.
- **Morphological cleanup:** binary opening to kill single-pixel speckle, closing to fill small gaps, then `remove_small_objects` / `remove_small_holes`. Calibrate the minimum object size against EFFIS's operational floor of **≈30 ha** (§4.7) — a defensible number rather than an arbitrary one.
- **Perimeter:** `skimage.measure.find_contours` on the cleaned mask, then Douglas–Peucker (`shapely.simplify` or `skimage.measure.approximate_polygon`). **Active contours / morphological geodesic active contours** (`morphological_geodesic_active_contour`) can refine the boundary onto the NBR gradient — a nice touch if time allows.

### 4.5 ⚠️ The perimeter-length trap

**[PRIMARY]** The Niebla fire is reported with **"more than 200 km of perimeter"** for ≈39 821 ha ([Wikipedia, citing EFE/ABC 2026-09-09](https://es.wikipedia.org/wiki/Incendio_forestal_de_Niebla)). A circle of that area has a perimeter of ≈70 km. So the real perimeter is ≈3× the circle-equivalent.

**[INFERRED]** Perimeter length is **not a stable quantity** — it is a fractal-like measure that grows as your simplification tolerance shrinks, and a pixel-boundary trace will overestimate it badly (staircase effect inflates a straight diagonal by up to √2). Therefore:

> **Never report a perimeter number without stating the simplification tolerance and the pixel size.** Report it as e.g. "212 km at 20 m simplification tolerance", and ideally give the value at two or three tolerances to show you understand the sensitivity. Area is robust; perimeter is not. This single caveat will distinguish you from teams that print a number with three decimal places.

### 4.6 **[MEASURED]** Self-consistency: hotspots are inside the scar

| Scene | QuickFire hotspots | median NBR at hotspots | fraction with NBR < 0 |
|---|---|---|---|
| huelva | 8 658 | −0.298 | **0.911** |
| guadalajara | 577 | −0.262 | **0.993** |

Active fire sits firmly inside the low-NBR region, as physical sense demands. **This is a free validation metric with no ground truth required** — report it. If a future scene gives you hotspots *outside* the scar, that is a genuine warning flag worth surfacing in the UI (it can be real at a fast-moving fire front, or it can be a detector error).

### 4.7 Area and perimeter in real units — the honest treatment

**The hard constraint:** these JPEGs carry **no CRS, no geotransform, no bbox**. I checked every metadata field; there is only JFIF density and an ICC profile.

**[PRIMARY]** What the export conventions tell us:
- EO Browser / Copernicus Browser offer JPG, PNG, **KMZ and GeoTIFF** under the *Analytical* option (sign-in required) ([EO Browser user guide](https://www.sentinel-hub.com/explore/eobrowser/user-guide/)). **JPG/PNG are not georeferenced; KMZ and GeoTIFF are.**
- Georeferenced output is capped: *"split your area in several smaller images... or choose a bit lower resolution to stay within the limits of 2500px"* ([CDSE FAQ](https://documentation.dataspace.copernicus.eu/FAQ.html)).
- The *High-res print* option gives large areas at high resolution but the data *"is though not georeferenced"* (same FAQ).

**[INFERRED]** This explains your files exactly: `huelva` and `guadalajara` are **2500 × 1546** — precisely at the 2500 px cap, so standard image download. `madrid-avila` is **9930 × 6141**, far past the cap, so it is a *High-res print* export and **definitively not georeferenceable**.

**[MEASURED] I tried to recover the pixel size from the pixels themselves, and it does not work.** B12 and B8A are 20 m native while B04 is 10 m, so if the render grid were finer than 20 m the SWIR channels should show a step structure at period `20 m / mpp`. Measuring mean |horizontal first difference| by column phase mod 2/3/4:

- phase ratios are only **1.02–1.14**, and
- the **JPEG 8×8 block artifact produces a comparable or larger mod-8 ratio (1.10–1.23)**, swamping the signal.

So the test is **inconclusive** — the resampling is smooth (bilinear-like), which erases the step structure. One weak hint: in `madrid-avila`, True Color mean|Δ| is 12.8 versus SWIR 6.1, consistent with 20 m bands smoothly upsampled onto a finer grid, but this is not strong enough to quantify. **You cannot get metres-per-pixel out of the JPEG.**

**[INFERRED] Order-of-magnitude cross-check against the real fires.** Using my crude scar fractions and the reported final burned areas:

- guadalajara: scar ≈ 12.9 % of 2500×1546 ≈ 500 000 px; against ~32 000 ha ⇒ ≈25 m/px
- huelva: scar ≈ 16.2 % ≈ 627 000 px; against ~15 000 ha (partial, image is day 2 of 15) ⇒ ≈15 m/px

Both crude (my scar mask over-detects; the images predate the final extent). **Conclusion: the renders are of order 10–30 m/px.** Not precise enough to quote.

> **Therefore, the defensible design:**
> 1. Make ground resolution an **explicit required parameter** — `--metres-per-pixel` or `--bbox` (from which m/px = bbox_width_m / image_width_px).
> 2. Default to **10 m/px** (Sentinel-2's finest) and **label every derived figure as provisional** when the parameter was not supplied.
> 3. Print area in **pixels and hectares side by side**, with the assumed m/px stated in the same sentence. Always draw a scale bar, whose length is honest about the assumption.
> 4. Tell the user how to get the real number: re-export from the Browser as **GeoTIFF or KMZ** and read the geotransform, or paste the bbox from the Browser URL. Accept a GeoTIFF if given one — then everything becomes exact.
> 5. **[PRIMARY]** Benchmark your minimum mappable object against EFFIS: it maps burnt scars of *"approximately 30 hectares"* and explicitly does not map unburned islands below imagery resolution ([EFFIS rapid damage assessment](https://forest-fire.emergency.copernicus.eu/about-effis/technical-background/rapid-damage-assessment)).
>
> **Stating the assumption loudly is worth more marks than inventing a number.** The rubric rewards justifying technical decisions; this is one of the easiest places to visibly do that.

---

## 5. Validation with no ground truth

### 5.1 FIRMS / VIIRS active fire — the independent cross-check

**[PRIMARY]** [NASA FIRMS API](https://firms.modaps.eosdis.nasa.gov/api/area/), area service. Free `MAP_KEY`. Path pattern: `MAP_KEY / source / area-coordinates / day-range [/ start-date]`; CSV is selected in the path. Omitting the date gives the most recent data.

- **Sources** include VIIRS NOAA-21 NRT, VIIRS S-NPP NRT, VIIRS S-NPP standard processing.
- **Day range** 1–5 days per query (per the [USFS variant docs](https://firms2.modaps.eosdis.nasa.gov/usfs/api/area/)).
- **Rate limit** 5 000 transactions per 10 minutes; a multi-day request may count as several.
- **Archive** for data older than 7 days: [download page](https://firms.modaps.eosdis.nasa.gov/download/), shapefile/CSV/JSON. VIIRS S-NPP 375 m coverage starts **2012-01-20**; MODIS C6.1 starts **2000-11-01**. ⚠️ **Your scenes are July–August 2026, so you need the archive route, not NRT.**
- [Python tutorial](https://firms.modaps.eosdis.nasa.gov/content/academy/data_api/firms_api_use.html).
- **[UNVERIFIED]** the exact bounding-box coordinate order — not stated in any page I reached. Check the area docs page before coding.

**How to use it honestly:** VIIRS is **375 m** against your ~10–30 m. So the check is **"does each of my detected clusters have a FIRMS detection within ~500 m on the same date?"** and **"are there FIRMS detections I missed entirely?"** — presence/location agreement, *never* per-pixel IoU. Also note VIIRS overpass time differs from Sentinel-2's (~10:30 local descending), so same-date is not same-instant; a fire can start or die between them. Say so.

### 5.2 Copernicus EMS — these exact fires were mapped

**[PRIMARY]** **EMSR913 — "Wildfire in Huelva, Spain"**, [activation page](https://mapping.emergency.copernicus.eu/news/wildfire-in-huelva-spain-emsr913/), dated **2026-08-07**. CEMS was requested to provide **burnt area delineation and damage assessment** emergency mapping for an on-going, spreading fire in western Andalusia.

> **Your `huelva` scene is dated 2026-08-08. The activation is 2026-08-07. This is the same fire, one day apart, with an official expert-delineated burnt-area product. It is the best validation reference you will find — and it is a strong slide: "our automatically derived perimeter, compared against Copernicus EMS EMSR913."**

Products: [EMSR913 situational reporting](https://mapping.emergency.copernicus.eu/activations/EMSR913/reporting/). **[UNVERIFIED]**: the activation news page does not state the requesting authority, the satellites used, direct download links, the data licence, or any hectare figure — fetch the activation page itself to get the vectors.

Other Huelva activations, for context: **EMSR881** (June 2026, forest fire near Villanueva de los Castillejos) and **EMSR931** (September 2026, situational reporting). **[UNVERIFIED]** I found **no** EMSR activation for the July 2026 Guadalajara or Ávila/Madrid fires, despite searching — surprising given their size, so search the CEMS portal directly rather than trusting this absence.

Season context **[PRIMARY]**: by 2026-09-30 CEMS had received **47** Rapid Mapping wildfire activation requests, versus 34 for all of 2025.

### 5.3 Independent scale and extent references for your three scenes

**[PRIMARY]** — note the sources genuinely disagree; quote ranges, not point values.

| Scene | Fire | Dates | Reported burned area |
|---|---|---|---|
| `huelva` 2026-08-08 | **Niebla** (Huelva/Sevilla, 11 municipalities; started at paraje de Raboconejo) | declared 2026-08-06, extinguished 2026-08-21 | **39 821 ha** final ([Wikipedia](https://es.wikipedia.org/wiki/Incendio_forestal_de_Niebla) citing EFE/ABC 2026-09-09); ≈33 000 ha per Copernicus and ≈38 000 ha "recorridas" ([tecnobosque analysis](https://tecnobosque.es/analisis-tecnico-incendio-de-niebla-huelva/)); >31 000 ha as of 2026-08-13 ([Infobae](https://www.infobae.com/espana/2026/08/13/el-incendio-de-niebla-huelva-pierde-fuerza-tras-arrasar-31000-hectareas-y-dejar-a-700-vecinos-desalojados/)). Perimeter **>200 km**. |
| `guadalajara` 2026-07-21 | **La Mierla** (Sierra Norte) and **Selas** (Alto Tajo) | detected 2026-07-21 | La Mierla ≈**32 000–35 000 ha**, 34 villages evacuated ([Que.es](https://www.que.es/2026/07/23/incendio-guadalajara-2026-hectareas-evacuados/)); Selas ≈1 700 ha on the day, ≈2 600–2 800 ha final ([CMM](https://www.cmmedia.es/noticias/castilla-la-mancha/guadalajara/incendio-forestal-selas-guadalajara.html)) |
| `madrid-avila` 2026-07-26 | **Burgohondo** (Ávila) + Madrid | 2026-07-26 | Burgohondo >**50 000 ha** — described as the largest in Spanish recorded history; Ávila + Madrid combined >**70 000 ha** ([eldiario.es live blog, 2026-07-26](https://www.eldiario.es/sociedad/ultima-hora-incendios-incendios-madrid-avila-castello-avanzan-control-100-000-afectados-noche-lucha-llamas_133_13407366.html)) |

⚠️ **Crucial caveat: every figure above is the fire's *final* extent, while each image is a single day mid-event.** `huelva` is day 2 of a 15-day fire; `guadalajara` is the detection day. **Your detected area should be substantially smaller than these numbers, and that is correct, not an error.** Do not "calibrate" to match them.

Also note **[PRIMARY]**: tecnobosque reports ≈33 000 ha burnt versus ≈38 000 ha "recorridas/afectadas", the difference being **unburned islands inside the perimeter**. That distinction matters for your deliverable — decide and state whether you report the *perimeter-enclosed* area or the *burnt* area, and consider reporting both. EFFIS explicitly does not map unburned islands below resolution (§4.7).

### 5.4 Self-consistency checks (no external data needed)

Build these into the pipeline and print them — they are cheap and they are exactly what "justify your technical decisions" means:

1. **Hotspot containment** — fraction of active-fire detections falling inside the burned mask. **[MEASURED]** baseline 0.911 / 0.993 (§4.6).
2. **Cross-composite agreement** — `SWIR_B` vs `TC_R` should track (same band). **[MEASURED]** corr 0.91–0.95. A drop flags mis-registration or a different export setting, i.e. an input-sanity alarm.
3. **Mask stability under threshold perturbation** — recompute area at NBR threshold ±0.02 and report the spread as an uncertainty band. This turns "we picked a threshold" into a quantified confidence interval.
4. **Smoke/cloud leakage audit** — report what fraction of the burned mask also satisfies the cloud test and the smoke test (`D > 1`). Should be near zero; if not, your gating is failing.
5. **Known-negative sampling** — the scene corners are usually outside the fire; mask statistics there estimate your false-positive rate for free.
6. **QuickFire agreement** (when `Wildfires` is present) — decode it and compare against your SWIR-only Murphy-partial detector. Report precision/recall of your fallback against the decode. **[MEASURED]** the naive `B12`-only version scores recall 0.95–0.999 but over-detects 13–45× (§1.5), so this check has real teeth.

---

## 6. Environment note

**[MEASURED]** In the current environment `python3` is **3.12.3**, `PIL` **10.2.0** is installed system-wide (`python3-pil`), but **`numpy`, `scipy`, `scikit-image`, `scikit-learn` and `cv2` are all absent.** All measurements in this document were made in a venv created with:

```
python3 -m venv --system-site-packages venv && ./venv/bin/pip install numpy
```

Budget time for `pip install numpy scipy scikit-image scikit-learn shapely` early — and pin them in `requirements.txt`, because "software quality" is on the rubric. Note PIL needs `Image.MAX_IMAGE_PIXELS = None` to open the 9930×6141 `madrid-avila` files, which exceed its decompression-bomb guard.

---

## 7. ⛔ What is NOT possible with these inputs

Do not spend hours here.

1. **dNBR and every published burn-severity class.** Needs a pre-fire acquisition. You have one date per scene. This kills the Key & Benson / EFFIS severity tables (§2.2), Sentinel Hub's `burned_area` multitemporal script, and all dBAIS2 work. **You can only do single-date, relative severity** — and you must say so.
2. **Anything requiring B11 (SWIR-1, 1610 nm).** It is in neither composite and §2.5 proves it is not recoverable from the `Wildfires` render. This rules out: **NBR2**, **MIRBI**, the **Fire Boundary** script, the **Burned Area Visualization** script, **Murphy's `B12/B11 ≥ 1.4` test**, Murphy's potential-fire test, and the **`B12/B11` hot-soil rejector**. It is also the one band blocking Prithvi-BurnScars.
3. **Anything requiring B05–B07 (red-edge).** Kills **BAIS2** outright — the Sentinel-2-specific burned-area index, the one best suited to the task in principle.
4. **Anything requiring B08, B09, B10.** B8A substitutes acceptably for B08. B10 does not exist in L2A at all, so the textbook cirrus-based cloud test is unavailable to *everyone*, not just you — §4.3 is your replacement.
5. **The Sen2Cor Scene Classification Layer (SCL) and cloud probability (CLP).** Not in a rendered JPEG. Note `cdse.js` had to work around exactly this absence with its own `isCloud()` (§1.3).
6. **Reflectance above 0.4 in any channel.** Hard-clipped by the gain-2.5 render. So you can detect *that* a pixel is saturated-hot but **cannot measure how hot** — no fire radiative power, no temperature retrieval, no sub-pixel fire-area fraction.
7. **Absolute geolocation, area or perimeter in metres.** No CRS, no geotransform, no bbox; §4.7 shows the pixel size cannot be recovered from the pixel data. Everything metric is conditional on a user-supplied parameter.
8. **Per-pixel validation against ground truth.** VIIRS is 375 m; EMS vectors are a different instant. Presence/location agreement only.
9. **Geospatial foundation models off the shelf.** Prithvi/Clay/DOFA want 6–13 band reflectance with sensor-specific normalisation. Channel surgery plus fine-tuning is not a 48 h task. SAM/SAM2 is the only FM that natively eats 3-channel 8-bit.
10. **Training a segmentation model on these scenes.** Three images, no labels. Any apparent success would be memorisation, and the judges explicitly test on unseen scenes.
11. **Trusting the `Wildfires` layer under cloud.** `cloudAvoidance = 1` by default actively *suppresses* hotspots where `isCloud()` fires or `B02 ≥ 0.8` (§1.3). A fire beside bright cloud is invisible in that render. Your SWIR-only fallback must still run there, and the UI should flag it.
12. **Assuming all scenes ship a `Wildfires` composite.** `madrid-avila` does not. Degrade gracefully; never crash, never silently claim equal confidence.
13. **Assuming the next scene uses the same tone curve.** §1.3 shows EO Browser and Copernicus Browser QuickFire variants differ materially. Key on gain-invariant normalised differences and on structural signatures (`R − B` for hotspots), not on absolute RGB values.

---

## 8. Open questions / unverified

**Blocking-ish, worth 30 min if someone has time:**

1. **The Copernicus Browser's actual built-in `True color` and `SWIR` layer definitions.** I could not retrieve them. The custom-scripts versions (gain 2.5, linear) do **not** explain the ≈2.2 gamma I measured between the two renders (§1.2). The gamma is presumably a layer *styling* parameter outside the evalscript. My attribution of it to True Color is **[INFERRED]** from reflectance plausibility, not documented. *Tried and failed:* `GetCapabilities` on `sh.dataspace.copernicus.eu` (404); no public `eo-browser-custom-scripts` repo; the CDSE Sentinel-2 page documents only `layerId=1_TRUE_COLOR` with no band/stretch info. *Next step:* open the layer in Copernicus Browser and use its "show evalscript" / layer-settings panel, which exposes gain and gamma directly. **This is the highest-value remaining unknown** — it determines whether cross-composite arithmetic is exact or approximate. (Mitigation already in place: the recommended pipeline uses only *within-composite* normalised differences, which are immune to it.)
2. **Whether the Copernicus Browser `Wildfires` layer is exactly `cdse.js`** at the current version, or a modified fork. Strong circumstantial evidence it is (§1.4: correct tier colour families, forward-model correlation 0.94–0.98, and the measured blue suppression matching `manualCorrection[2] = −0.05` and `sMin = 0.15`), plus secondary press reporting. But no first-party CDSE documentation page for the layer. Also note the `markuse_fire` README is titled *"Wildfire visualization"* while the layer/filename says *"Wildfires"*.
3. **EMSR913 product vectors, download links, licence and hectare figure.** The news page states none of these (§5.2). Fetch [the activation page](https://mapping.emergency.copernicus.eu/activations/EMSR913/reporting/) directly.
4. **FIRMS bounding-box coordinate order.** Not documented on any page I reached.

**Secondary — flagged so nobody cites them as fact:**

5. **BAIS2 threshold 0.865** (Filipponi, Sicily July 2017) — reaches me only via secondary citation; the primary PDFs (sciforum slides, MDPI *Remote Sensing* 11(6) 622) both returned **HTTP 403**. The *formula* is solid (taken from Sentinel Hub's own implementation).
6. **Key & Benson dNBR class breaks.** The 100/270/440/660 table is verified as **EFFIS's** adaptation; I could not confirm those exact breaks in the original FIREMON chapter, which prescribes scene-specific tuning instead (§2.2).
7. **NBR2 ownership.** Attributed variously to Lutes et al. 2006 and Key & Benson 1999; found **no USGS page** defining it. (Moot — needs B11.)
8. **MIRBI.** Could not reach Trigg & Flasse. Sources disagree on 2000 vs 2001, and one prints the coefficient as 0.98 rather than 9.8. (Moot — needs B11.)
9. **BAI attribution** — Chuvieco et al. 2002 vs Martín 1998.
10. **Murphy et al. (2016) original thresholds.** I have them via the ActiveFire reimplementation (arXiv:2101.03409), not from RSE 177:78–88 itself. The reimplementation is explicit and credible, but it is one step removed.
11. **AFD-S2 per-biome numeric thresholds** — paywalled.
12. ~~**Sen2Fire licence**~~ — **resolved: CC BY 4.0**, 6.3 GB, confirmed on the [Zenodo record](https://zenodo.org/records/10881058).
13. **Landsat-8 ActiveFire *dataset* licence** — the arXiv paper is CC BY-NC-ND 4.0 but says nothing about the data; check the GitHub repo. ⚠️ If it is NC, that may matter for a sponsored hackathon.
14. **"Kato & Enomoto"** active-fire variant — mentioned in the brief; I could not locate it. The third algorithm in the ActiveFire paper is **Kumar & Roy (2018)**. Possible misattribution.
15. **Zero-shot SAM burned-area mapping** (NBR/NBR2/NDVI composites fed to SAM) — surfaced via search snippet only; primary record not opened.
16. **No EMSR activation found for the July 2026 Guadalajara or Ávila/Madrid fires** — surprising given >50 000 ha. Likely a search failure rather than a real absence; check the CEMS portal directly.
17. **Quantitative AOD-by-wavelength for smoke** across Sentinel-2 bands — not found. The qualitative SWIR-penetrates-smoke claim is well supported; the measured discriminator in §4.3 does not depend on the numbers.

**My own measurements that deserve a second pair of eyes:**

18. The **≈2.2 gamma** between composites (§1.2) is robust across all three scenes (RMSE 4.9–11.0 DN), but my inference about *which* composite carries it rests on reflectance plausibility. Re-derive it if you can get a GeoTIFF export of the same scene, which would settle it instantly.
19. My **class definitions in §4.2 are rules, not ground truth.** The "cloud" and "smoke" classes in particular are percentile-defined and may contain each other at the edges. The `D` separation (+2.1 vs −0.5) is wide enough to survive this, but the absolute percentages are soft.
20. The **pixel-size cross-check in §4.7** (≈15–25 m/px) uses my crude scar mask against *final* fire extents for images taken mid-event. It is an order-of-magnitude argument only. Do not quote it as a measurement.

---

## Appendix — primary source index

**Evalscripts (raw source, fetched)**
- [`markuse_fire/cdse.js`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/markuse_fire/cdse.js) — QuickFire, Copernicus Browser ← **the `Wildfires` layer**
- [`markuse_fire/script.js`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/markuse_fire/script.js) — QuickFire, EO Browser variant
- [`markuse_fire/README.md`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/markuse_fire/README.md) — provenance, CC BY 4.0, Markuse blog Sept 2022
- [`true_color/script.js`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/true_color/script.js) — gain 2.5
- [`swir-rgb/script.js`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/swir-rgb/script.js) — `[2.5·B12, 2.5·B8A, 2.5·B04]`
- [`nbr/script.js`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/nbr/script.js) — NBR
- [`bais2/script.js`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/bais2/script.js) + [README](https://github.com/sentinel-hub/custom-scripts/blob/main/sentinel-2/bais2/README.md) — BAIS2 formula and value ranges
- [`burned_area_ms/script.js`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/burned_area_ms/script.js) — EO Browser wildfires-theme burned-area rule
- [`burned_area/script.js`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/burned_area/script.js) — multitemporal dNBR
- [`fire_boundary/script.js`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/fire_boundary/script.js) — `8.5·(B12−B11)/(B12+B11+0.25)`
- [`false-color-urban-rgb/script.js`](https://raw.githubusercontent.com/sentinel-hub/custom-scripts/main/sentinel-2/false-color-urban-rgb/script.js) — `HighlightCompressVisualizer(0, 0.4)` example
- [custom-scripts composites page](https://custom-scripts.sentinel-hub.com/sentinel-2/composites/) — band-combination table

**Agency documentation**
- [CDSE Evalscript Utilities](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Evalscript/Utilities.html) / [SH Utility Functions](https://docs.sentinel-hub.com/api/latest/evalscript/functions/) — `HighlightCompressVisualizer`
- [CDSE Sentinel-2 L2A](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html) — bands, resolutions, baseline 04.00 offset
- [CDSE FAQ](https://documentation.dataspace.copernicus.eu/FAQ.html) — 2500 px georeferencing limit, `RESX/RESY`, high-res print not georeferenced
- [EO Browser user guide](https://www.sentinel-hub.com/explore/eobrowser/user-guide/) — export formats
- [EFFIS Fire Severity](https://forest-fire.emergency.copernicus.eu/about-effis/technical-background/fire-severity) — dNBR class breaks
- [EFFIS Rapid Damage Assessment](https://forest-fire.emergency.copernicus.eu/about-effis/technical-background/rapid-damage-assessment) — operational method, ≈30 ha floor, 20 m S2 since 2018
- [Copernicus EMS mapping portal](https://mapping.emergency.copernicus.eu/) / [EMSR913](https://mapping.emergency.copernicus.eu/news/wildfire-in-huelva-spain-emsr913/)
- [NASA FIRMS API — area](https://firms.modaps.eosdis.nasa.gov/api/area/), [archive download](https://firms.modaps.eosdis.nasa.gov/download/), [Python tutorial](https://firms.modaps.eosdis.nasa.gov/content/academy/data_api/firms_api_use.html)

**Papers**
- Key & Benson (2006), *Landscape Assessment*, FIREMON RMRS-GTR-164-CD — [PDF](https://www.fs.usda.gov/rm/pubs/rmrs_gtr164/rmrs_gtr164_13_land_assess.pdf) *(returns 403 to automated fetchers; open in a browser)*
- Murphy et al. (2016), HOTMAP, *Remote Sens. Environ.* 177:78–88 — [DOI](https://doi.org/10.1016/j.rse.2016.02.027)
- Schroeder et al. (2016/2017), Landsat-8 reflectance-based active fire — [Tandfonline](https://www.tandfonline.com/doi/full/10.1080/17538947.2017.1391341)
- de Almeida Pereira et al. (2021), ActiveFire — [arXiv:2101.03409](https://arxiv.org/pdf/2101.03409) · thresholds for Murphy / Schroeder / Kumar-Roy
- Hu et al. (2021), AFD-S2 multi-criteria — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0303243421000544)
- Filipponi (2018), BAIS2 — [DOI 10.3390/ecrs-2-05177](https://doi.org/10.3390/ecrs-2-05177) · [RG PDF](https://www.researchgate.net/publication/323964124_BAIS2_Burned_Area_Index_for_Sentinel-2)
- Xu, Berg & Haglund (2024), Sen2Fire, IGARSS — [arXiv:2403.17884](https://arxiv.org/abs/2403.17884)
- California S2 Active-Fire Segmentation Dataset (2026) — [arXiv:2609.16199](https://arxiv.org/pdf/2609.16199) · [Zenodo](https://doi.org/10.5281/zenodo.22713948)
- Osco et al. (2023), SAM for remote sensing — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1569843223003643) · [arXiv:2306.16623](https://arxiv.org/pdf/2306.16623)

**Model / dataset cards**
- [Prithvi-EO-2.0-300M-BurnScars](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-300M-BurnScars) · [Prithvi-EO-2.0 paper](https://arxiv.org/pdf/2412.02732) · [NASA-IMPACT repo](https://github.com/NASA-IMPACT/Prithvi-EO-2.0)
- [HLS Burn Scars dataset](https://huggingface.co/datasets/ibm-nasa-geospatial/hls_burn_scars)
