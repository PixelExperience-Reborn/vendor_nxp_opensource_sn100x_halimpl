# PixelExperience-Reborn Android 17 — row 172: archived SN100x HAL and current NFC Mainline

**Review date:** 2026-11-07. **Device scope:** independent PE-Reborn for POCO F5 Pro / Redmi K60 (`mondrian`, SM8475), after a functional independent AOSP17 platform base exists.

**Decision: DO NOT activate historical `vendor/nxp/opensource/sn100x/halimpl` in the Android17 manifest or product.** Use official AOSP17 `platform/hardware/nxp/nfc` for controller HAL, `platform/packages/modules/Nfc` for NFC Mainline/APEX, and `platform/system/secure_element` for OMAPI/SE. NXP's contemporary Android17 `br_ar_17_aosp_mainline` is a verified **source-only comparison candidate**, not another source tree to install in parallel. The actual NFC controller, vendor firmware, eSE and specific Xiaomi SKU for mondrian have **not** been established by authoritative device evidence here.

## Pinned sources and provenance

| Source | Exact commit/tree | Evidence / role |
| --- | --- | --- |
| Archived PE `vendor_nxp_opensource_sn100x_halimpl` `seventeen` | commit `4febf025eb375939005779f133b6723e449062f0`, tree `af032a30031fd5c27f5435cf8792c7f1cc22688d`, dated 2022-03-30 | Historical 131-file NFC HAL, HIDL 1.1/1.2 wrappers, NFC NCI native library, eSE/JCOP/LS support, parser and example `libnfc-nci.conf`. Last commit is a Soong parser namespace fix, not Android17 compatibility proof. |
| Official Android17 NFC HAL | `platform/hardware/nxp/nfc` `android-17.0.0_r1`, commit `68931d93d3b2ccfc71553cb03088fe5d6fb5dd30`, tree `8386a3c67e07f5fe492c92d1888c256bbc37d48b` | Selected Android17 owner, `android.hardware.nfc-service.nxp` and the frozen NXP vendor AIDL interface (proven in row 169). |
| Current NXP Android17 vendor reference | `NXPNFCProject/nfcandroid_nfc_hidlimpl` `br_ar_17_aosp_mainline`, commit `debec247cea5570d259db3138124201e3769a728`, tree `31be748946aaf58dcf86034804db69c53a4ac3a7`, version `17.07.00` | Current NXP NFCC family release (PN557/PN560/SN100/SN110/SN220/SN300), modern native NFC AIDL V2 + vendor NXP AIDL V1, controller-specific example configs, observe mode, low power, transport and Wired SE code. Supported families are **not a device bill of materials**. |

Sources:
- https://github.com/PixelExperience-Reborn/vendor_nxp_opensource_sn100x_halimpl/tree/seventeen
- https://android.googlesource.com/platform/hardware/nxp/nfc/+/refs/tags/android-17.0.0_r1
- https://github.com/NXPNFCProject/nfcandroid_nfc_hidlimpl/tree/br_ar_17_aosp_mainline

## Actual archived build graph and risks

1. `SN100x/Android.bp` declares **`nfc_nci.nqx.default.hw`**, a vendor `cc_library_shared` with `hidl_defaults`, linking `android.hardware.nfc@1.0/@1.1/@1.2`, `vendor.nxp.hardware.nfc@2.0`, `android.hardware.secure_element@1.0`, `libhidlbase` and legacy hardware APIs. This is not an Android17 stable AIDL service, nor a Mainline NFC module.
2. Root `Android.bp` contains legacy `se_nq_extn_client`, `jcos_nq_client` and `ls_nq_client`; it exports `libese_client_headers`. The archive's `SN100x/halimpl/libnxpparser/Android.bp` declares `soong_namespace {}` to isolate `nxp_nci_parser`. The 2022 archived commit notes an already-defined `nxp_nci_parser` in the other `hardware/nxp/nfc` tree. **Combining both trees risks duplicated service and Soong module names**, even though a namespace reduces one particular collision.
3. `nfc_vendor_product.mk` conditionally sets `TARGET_USES_NQ_NFC` for historical platform families `sdm845`, `sdm710`, `msmnile`, `kona`, `lito`, `lahaina` etc., and hardcodes `vendor.nxp.hardware.nfc@2.0-service` plus `nfc_nci.nqx.default.hw` as product packages; **SM8475 is not explicitly listed**. Do not infer that a macro or an inherited makefile selects mondrian correctly. The service package may originate from the separate row 173 `sn100x/hidlimpl`; this audit does not assume the archived HAL library itself installs the service.
4. The makefile copies a historical generic `SN100x/halimpl/libnfc-nci.conf` and **advertises NFC, MIFARE, HCE, HCE-F, eSE and UICC features**. These are product-feature declarations, **not proof** the underlying chip, SE routes or payment/UICC support exist on mondrian. Never grant features or copy the config without verified controller/SE behavior.
5. The old conf contains `NFC_DEBUG_ENABLED=1`, `SCREEN_OFF_POWER_STATE=1`, `POLLING_TECH_MASK=0x4F`, `NFA_MAX_EE_SUPPORTED=0x03`, and `NXP_PRFD_TECH_SE=0x01`. This is an old example stack profile, not an acceptable device power/routing configuration. In particular, do **not** import arbitrary SE/eSE routing, polling or always-on controller power settings.
6. The source has NFC firmware download code, I²C access, SPI/SPM, DTA/self-tests and vendor `INxpNfc` HIDL 2.0 with `resetEse`, `setEseUpdateState`, JCOP/LS status methods. Those methods are capable of materially affecting SE state and should never be activated just because the source exists.
7. Historic `1.1/NxpNfcService.cpp` and `1.2/NxpNfcService.cpp` call `initializeEseClient()`, `checkEseClientUpdate()` and `perform_eSEClientUpdate()` during startup. Their mere presence does **not** prove that these wrapper source files were part of an installed product, but the boot-time SE provisioning design is a significant safety and integrity concern. Do **not** perform old JCOP/LS/eSE firmware download on device.
8. `SN100x/halimpl/libnxpparser/Android.bp` is a vendor parser library; retain only as evidence for debugging modern native NCI if a reproducible problem demands it. No extra parser module is needed in the Android17 product by default.

## Contemporary Android17 architecture

- Official AOSP17 `hardware/nxp/nfc` already carries the **stable NXP vendor AIDL contract**, and NFC Mainline is owned by `packages/modules/Nfc`; do not re-enable legacy `nfc_nci.nqx.default.hw` or HIDL NFC services.
- NXP 17.07.00 provides `android.hardware.nfc2-service.nxp`, `android.hardware.nfc-V2-ndk`, `vendor.nxp.nxpnfc_aidl-V1-ndk`; `snxxx/aidl/2.0/nfc2-service-nxp.xml` declares the two **different** AIDL instances `android.hardware.nfc.INfc/default` (version 2) and `vendor.nxp.nxpnfc_aidl.INxpNfc/default`. Only one system `INfc/default` service may be selected.
- Newer NXP HAL has `snxxx/halimpl_v2/observe_mode` and `power-tracker`, `NfccTransportFactory` / I²C transport and Wired SE support. These are modern development references. Their physical availability and security- and power-policy requirements on **mondrian are unknown**.
- Its `snxxx/halimpl_v2/conf` contains **controller-specific *examples*** (SN100, SN110, SN220, SN300, PN557, PN560). Do not assume they are ready-made Xiaomi settings. A current source revision does not guarantee compatibility with existing vendor blobs, secure element or APEX signing.
- An up-to-date variant should be evaluated as a **targeted, source-level delta** against the *official* NXP source already selected. The source-checking CI can report changed/added/removed common HAL paths for a future deliberate port, but will **not** automatically overwrite an official module, insert an unverified vendor binary or alter the default checkout.

## Exact source-delta assessment — official AOSP17 vs NXP 17.07.00

[Verified source comparison CI #42317340840](https://github.com/PixelExperience-Reborn/vendor_nxp_opensource_sn100x_halimpl/actions/runs/42317340840) compared **actual Git blob IDs**, not README feature claims, inside the `snxxx/` HAL subtree at pinned commits `68931d93d3b2...` (AOSP17 r1) and `debec247cea5...` (NXP17 17.07.00):

| Exact Git source files | Count |
| --- | ---: |
| Shared paths in both source trees | **168** |
| Shared paths with different content blobs | **84** |
| Files present only in the NXP 17.07.00 snapshot | **0** |
| Files present only in the official AOSP17 r1 tree | **118** |

**Important:** The newer *release date* of an upstream vendor branch does **not** make it a complete superset of the actual AOSP17 HAL. This comparison cannot prove which revisions fix more bugs, which binary ABI is correct, or whether any path is selected by the current product. Whole-tree replacement would remove **118 official AOSP17 source paths**, including older compatibility-layer files under `snxxx/halimpl/` and examples. Those files are **not necessarily used by the selected product**: losing them does not automatically cause a runtime regression, but their removal must be assessed deliberately. The 84 differing common files require semantic/ABI/security diff and tests before selecting individual changes. Only a genuine, device-specific improvement would justify a narrowly reviewed patch to the **existing** AOSP17 owner; no blanket import or duplicate module path.

The source checker logs a sample of changed paths and official-only paths, and probes whether NFC HAL service module names are present. These results are **not an Android17 build or a comparison of installed Xiaomi vendor firmware**.

## Service-source verification and explicit AIDL selection

[GitHub Actions #42317649855](https://github.com/PixelExperience-Reborn/vendor_nxp_opensource_sn100x_halimpl/actions/runs/42317649855) **SUCCESS**: the checker inspected `snxxx/Android.bp` and parsed `snxxx/aidl/2.0/nfc2-service-nxp.xml` from the **actual official Android17 r1** source. Official AOSP17 **already declares both** `android.hardware.nfc-service.nxp` and `android.hardware.nfc2-service.nxp`; its AIDL V2 VINTF fragment declares the **system** `android.hardware.nfc.INfc/default` and **vendor** `vendor.nxp.nxpnfc_aidl.INxpNfc/default`. The NXP 17.07.00 branch declares `android.hardware.nfc2-service.nxp` but not the other module.

**Consequences:** There is no reason to import the separate NXP17 Git tree merely to obtain an AIDL V2 NFC HAL. Already present in official source is **not** the same as product-selected, buildable, service-running or hardware-compatible. A future independent PE-Reborn mondrian product must explicitly select a single NFC HAL variant with correct NDK interfaces, OEM firmware, VINTF, SELinux, vendor AIDL instance and NFC Mainline/SE compatibility. Do not install both HAL variants or revive HIDL.

In this run all **25 staged AOSP17 manifest profiles** and **33/33 positive and adversarial manifest tests** passed. Exact source identity, Soong namespace and historical eSE boot-update hooks were checked. The **whole-platform build, vendor ABI, hardware operation and security certification remain untested**.

## Mondrian-specific acceptance gates

1. Verify actual installed NFCC chip part and firmware, kernel device node, vendor HAL service (including VINTF manifest), SELinux domain, SKU/region and NFC/eSE/UICC wiring. Primary evidence should come from the device's **official matched firmware / trusted hardware diagnostics** and user's own authorized device when available. Avoid basing PE-Reborn on an unrelated ROM; LF52406 LineageOS may be *exceptional last-resort read-only hardware evidence*, never an imported product/device baseline.
2. If a vendor proprietary HAL is required, identify its exact ELF dependencies and signed/compatible firmware; design a minimal **independent PE-Reborn** product around an AOSP17-compatible service. Do not introduce duplicate NFC AIDL/HIDL services or generic feature permissions without hardware tests.
3. Verify Soong/NDK/APEX build, frozen AIDL hash and VINTF/FCM, SELinux enforcing/neverallows, ownership of `INfc/default` and `INxpNfc/default`, secure element OMAPI and privileged-app routes. Do not grant `nciTransceive`/vendor reset/configuration to untrusted apps.
4. Validate NFC tag read/write, HCE, eSE/UICC *if actually present*, screen off/sleep power, wakeup, field stability, reboot/recovery and OTA; test CTS/VTS/NFC Mainline and inspect logcat+dmesg. Separate a real NFC-enabled test result from a static manifest PASS.
5. No default eSE/JCOP loader update, unknown firmware flash, calibration override, raw vendor NCI injection or bypassed SE permissions. Do not claim NFC WLC works just because NFC Mainline provides software support.

## Audit deliverables

Isolated `audit/a17-sn100x-halimpl-mainline-20261107`: detailed source evidence, pinned Python cross-tree checker, CI with actual official AOSP17/NXP17 Git fetch. Manifest branch receives a forbidden archive path/name guard plus two negative tests for unauthorized checkout/official HAL takeover. Matrix row 172 is updated. `seventeen` and the safe `default.xml` remain unchanged.

**Limits:** No full AOSP17/Soong/APEX build, finished independent device/product tree, real chip firmware check, hardware NFC/SE test or proof of mondrian compatibility.
