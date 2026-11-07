#!/usr/bin/env python3
"""AOSP17 PE-Reborn row 172: pinned legacy SN100x -> current NXP HAL boundary.

Source-only host audit. This does NOT compile AOSP, install NFC services,
identify mondrian NFCC, validate proprietary firmware or perform eSE tests.
"""
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

OLD_SHA = "4febf025eb375939005779f133b6723e449062f0"
OLD_TREE = "af032a30031fd5c27f5435cf8792c7f1cc22688d"
AOSP_SHA = "68931d93d3b2ccfc71553cb03088fe5d6fb5dd30"
AOSP_TREE = "8386a3c67e07f5fe492c92d1888c256bbc37d48b"
NXP_SHA = "debec247cea5570d259db3138124201e3769a728"
NXP_TREE = "31be748946aaf58dcf86034804db69c53a4ac3a7"
OLD_PATH = "vendor/nxp/opensource/sn100x/halimpl"
OLD_NAME = "vendor_nxp_opensource_sn100x_halimpl"


def require(ok, msg):
    if not ok:
        raise RuntimeError(msg)


def git(repo, *args):
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True,
        stderr=subprocess.PIPE).strip()


def pin(repo, ref, sha, tree, title):
    actual = git(repo, "rev-parse", f"{ref}^{{commit}}")
    require(actual == sha, f"{title}: commit {actual} != {sha}")
    actual_tree = git(repo, "rev-parse", f"{actual}^{{tree}}")
    require(actual_tree == tree,
            f"{title}: tree {actual_tree} != {tree}")
    return actual


def source(repo, ref, path):
    return git(repo, "show", f"{ref}:{path}")


def paths(repo, ref):
    return git(repo, "ls-tree", "-r", "--name-only", ref).splitlines()


def tree_blobs(repo, ref, base):
    records = git(repo, "ls-tree", "-r", ref, base).splitlines()
    output = {}
    for record in records:
        header, path = record.split("\t", 1)
        mode, kind, sha = header.split()
        if kind == "blob":
            output[path] = sha
    return output


def old_sn100x(repo):
    ref = pin(repo, "refs/remotes/origin/seventeen",
              OLD_SHA, OLD_TREE, "archived SN100x 2022")
    all_paths = paths(repo, ref)
    require(len(all_paths) == 131,
            f"archived SN100x 2022 source inventory changed: {len(all_paths)}")
    bp = source(repo, ref, "SN100x/Android.bp")
    base_bp = source(repo, ref, "Android.bp")
    make = source(repo, ref, "nfc_vendor_product.mk")
    parse = source(repo, ref, "SN100x/halimpl/libnxpparser/Android.bp")
    conf = source(repo, ref, "SN100x/halimpl/libnfc-nci.conf")
    manifest = ET.fromstring(
        source(repo, ref, "SN100x/extns/intf/nxpnfc/2.0/manifest.xml"))
    svc = source(repo, ref, "1.2/NxpNfcService.cpp")
    readme = source(repo, ref, "README.md")

    for symbol in ('name: "nfc_nci.nqx.default.hw"',
                   'defaults: ["hidl_defaults"]',
                   '"android.hardware.nfc@1.0"',
                   '"android.hardware.nfc@1.1"',
                   '"android.hardware.nfc@1.2"',
                   '"vendor.nxp.hardware.nfc@2.0"',
                   '"android.hardware.secure_element@1.0"',
                   '"libhidlbase"', "halimpl/tml/phTmlNfc_i2c.cc",
                   "halimpl/tml/spi_spm.cc"):
        require(symbol in bp, f"old SN100x HAL dependency changed: {symbol}")
    for module in ('se_nq_extn_client', 'jcos_nq_client',
                   'ls_nq_client', 'libese_client_headers'):
        require(f'name: "{module}"' in base_bp,
                f"old eSE/JCOP/loader module changed: {module}")
    require("soong_namespace {" in parse
            and 'name: "nxp_nci_parser"' in parse,
            "old NXP NCI parser Soong namespace/collision guard changed")
    require("TARGET_USES_NQ_NFC := true" in make
            and "sdm845" in make and "lahaina" in make
            and "sm8475" not in make and "mondrian" not in make,
            "old PN/SN platform-selection evidence changed")
    for item in ('vendor.nxp.hardware.nfc@2.0-service',
                 'nfc_nci.nqx.default.hw',
                 'android.hardware.nfc.ese.xml',
                 'android.hardware.nfc.uicc.xml',
                 'com.nxp.mifare.xml', 'libnfc-nci.conf'):
        require(item in make,
                f"archived vendor makefile copies/installs changed: {item}")
    for key in ('NFC_DEBUG_ENABLED=1', 'SCREEN_OFF_POWER_STATE=1',
                'POLLING_TECH_MASK=0x4F', 'NFA_MAX_EE_SUPPORTED=0x03',
                'NXP_PRFD_TECH_SE=0x01'):
        require(key in conf,
                f"archived NFC example config changed: {key}")
    hals = {(e.findtext("name"), e.findtext("version"), e.get("format"))
            for e in manifest.findall("hal")}
    require(("android.hardware.nfc", "1.0", "hidl") in hals
            and ("vendor.nxp.nxpnfc", "2.0", "hidl") in hals,
            "old VINTF NFC HIDL 1.0/NXP2.0 fragment changed")
    for fn in ("initializeEseClient();", "checkEseClientUpdate();",
               "perform_eSEClientUpdate();",
               "nfc_service->registerAsService();",
               "nxp_nfc_service->registerAsService();"):
        require(fn in svc,
                f"old HIDL service/eSE updater startup changed: {fn}")
    require("android::hardware::nfc::V1_2::INfc" in svc,
            "old HIDL 1.2 system NFC owner changed")
    require("11.02.00" in readme,
            "old SN100/NXP release references changed")

    print("PASS: 2022 SN100x 131-file tree + HIDL 1.x/native/eSE clients pinned")
    print("PASS: 2022 vendor make selects legacy NFC HIDL and generic eSE/UICC features")
    print("PASS: archived eSE boot-loader hooks and sample power/routing profile identified")
    print("PASS: old nxp_nci_parser Soong namespace and HIDL VINTF verified")
    print("OPEN: actual mondrian NFCC/SKU/firmware/eSE hardware evidence")


def official_nxp(repo):
    ref = pin(repo, "refs/tags/android-17.0.0_r1",
              AOSP_SHA, AOSP_TREE, "official AOSP17 NXP HAL")
    bp = source(repo, ref, "snxxx/Android.bp")
    aidl_bp = source(repo, ref, "intf/nxpnfc/aidl/Android.bp")
    iface = source(repo, ref,
                   "intf/nxpnfc/aidl/vendor/nxp/nxpnfc_aidl/INxpNfc.aidl")
    require('name: "android.hardware.nfc-service.nxp"' in bp,
            "official NXP AOSP17 HAL source module changed")
    require('name: "vendor.nxp.nxpnfc_aidl"' in aidl_bp
            and 'stability: "vintf"' in aidl_bp
            and "ndk: {" in aidl_bp,
            "official AOSP17 vendor NXP NDK/VINTF AIDL changed")
    for method in ("getVendorParam(", "setVendorParam(",
                   "resetEse(", "setNxpTransitConfig("):
        require(method in iface,
                "official NXP vendor AIDL lacks " + method)
    print("PASS: exact official AOSP17 source already owns native NXP vendor AIDL")


def modern_nxp(repo):
    ref = pin(repo, "refs/remotes/origin/br_ar_17_aosp_mainline",
              NXP_SHA, NXP_TREE, "current NXP 17.07.00 Android17")
    bp = source(repo, ref, "snxxx/Android.bp")
    manifest = ET.fromstring(
        source(repo, ref, "snxxx/aidl/2.0/nfc2-service-nxp.xml"))
    modern_paths = set(paths(repo, ref))
    for symbol in ('name: "android.hardware.nfc2-service.nxp"',
                   '"android.hardware.nfc-V2-ndk"',
                   '"vendor.nxp.nxpnfc_aidl-V1-ndk"',
                   'vintf_fragments: ["aidl/2.0/nfc2-service-nxp.xml"]'):
        require(symbol in bp,
                f"modern NXP17 native NFC HAL source changed: {symbol}")
    hals = {(h.findtext("name"), h.findtext("version"),
             h.findtext("fqname"), h.get("format"))
            for h in manifest.findall("hal")}
    require(hals == {
        ("android.hardware.nfc", "2", "INfc/default", "aidl"),
        ("vendor.nxp.nxpnfc_aidl", None, "INxpNfc/default", "aidl"),
    }, "modern NXP17 NFC V2 + vendor AIDL V1 instance ownership changed")
    for path in (
        "snxxx/halimpl_v2/hal/phNxpNciHal_PowerTrackerIface.cc",
        "snxxx/halimpl_v2/hal/phNxpNciHal_WiredSeIface.cc",
        "snxxx/halimpl_v2/observe_mode/ObserveMode.cc",
        "snxxx/halimpl_v2/tml/NfccTransportFactory.cc",
        "snxxx/halimpl_v2/tml/transport/NfccI2cTransport.cc",
        "snxxx/halimpl_v2/conf/SN1xx/sn100/gen-config-files/libnfc-nci.conf",
        "snxxx/halimpl_v2/conf/SN220/gen-config-files/libnfc-nci.conf",
    ):
        require(path in modern_paths,
                f"modern NXP17 transport/observe/SE/support file changed: {path}")
    require("17.07.00" in source(repo, ref, "README.md"),
            "NXP current release reference changed")
    print("PASS: current NXP17 native NFC AIDL V2 + vendor AIDL V1 exact VINTF")
    print("PASS: modern transport, observe mode, power tracking and Wired SE code")


def modern_delta(official, modern):
    # Git object IDs capture exact content identity for common paths
    # without copying large Git trees into the ROM or cherry-picking.
    old = tree_blobs(official, AOSP_SHA, "snxxx")
    current = tree_blobs(modern, NXP_SHA, "snxxx")
    overlap = set(old) & set(current)
    changed = sorted(p for p in overlap if old[p] != current[p])
    newer_only = sorted(set(current) - set(old))
    official_only = sorted(set(old) - set(current))
    require("snxxx/Android.bp" in overlap,
            "official and NXP17 lack shared Soong NFC HAL root")
    # Differences are merely review candidates, not automatic PE patches.
    print("INFO: official AOSP17 vs NXP17 exact SNXXX source blob delta:"
          f" shared={len(overlap)}, changed={len(changed)},"
          f" NXP-only={len(newer_only)}, AOSP-only={len(official_only)}")
    for path in changed[:12]:
        print("INFO: changed modern NXP file: " + path)
    if len(changed) > 12:
        print(f"INFO: {len(changed) - 12} more changed common source files")
    print("OPEN: review ABI/security/SE behavior before any targeted update")


def manifest(root):
    root = Path(root)
    default = ET.parse(root / "default.xml").getroot()
    require(len(default) == 1
            and default[0].tag == "include"
            and default[0].get("name") == "aosp17_pe_p2_kernel_configs.xml",
            "default AOSP17 safe source-only profile was altered")
    graph = ET.parse(root / "aosp17_pe_bootstrap.xml").getroot()
    owners = {x.get("path"): x.get("name") for x in graph.findall("project")}
    for path, name in (
        ("hardware/nxp/nfc", "platform/hardware/nxp/nfc"),
        ("packages/modules/Nfc", "platform/packages/modules/Nfc"),
        ("system/secure_element", "platform/system/secure_element"),
    ):
        require(owners.get(path) == name,
                "AOSP17 official NFC source owner changed at " + path)
    require(OLD_PATH not in owners and OLD_NAME not in owners.values(),
            "archived SN100x HIDL source unexpectedly activated")
    validator = (root / "tools/validate_aosp17_base_profiles.py").read_text()
    tests = (root / "tools/test_aosp17_manifest_entrypoint.py").read_text()
    require(f'if "{OLD_PATH}" in projects:' in validator
            and f'"{OLD_NAME}"' in validator,
            "row 172 path/name deny guard missing")
    for test in ("test_archived_sn100x_hal_cannot_enter_android17",
                 "test_archived_sn100x_hal_cannot_replace_official_aosp17_hal"):
        require(f"def {test}(" in tests,
                f"row 172 negative manifest test missing: {test}")
    subprocess.run(
        [sys.executable, str(root / "tools/validate_aosp17_base_profiles.py")],
        cwd=root, check=True)
    print("PASS: 25 approved manifest stages, official NFC/SE owners and row172 deny")


def main():
    require(len(sys.argv) == 5,
            "Usage: check_sn100x_halimpl_aosp17.py OLD_SN100X AOSP_NXP NXP17 MANIFEST")
    old, aosp, newer, mf = [Path(x).resolve() for x in sys.argv[1:]]
    require(all(x.is_dir() for x in (old, aosp, newer, mf)),
            "one or more source repositories are missing")
    old_sn100x(old)
    official_nxp(aosp)
    modern_nxp(newer)
    modern_delta(aosp, newer)
    manifest(mf)
    print("PASS: row 172 independent Android17 SN100x source and HAL boundary")
    print("NOT TESTED: Soong/NDK, NFC APEX, VINTF, SELinux, NFCC, eSE or mondrian")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, ET.ParseError,
            subprocess.CalledProcessError) as exc:
        print("FAIL:", exc, file=sys.stderr)
        sys.exit(1)
