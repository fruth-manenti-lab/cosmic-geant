#!/usr/bin/env python3
"""Create a 1 m diagonal face-mount GDML variant with black absorbing sidewalls."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "faceMountGeometry_1m_diagonal_sipms.gdml"
OUT = ROOT / "faceMountGeometry_1m_diagonal_sipms_black_sidewalls.gdml"


def replace_once(text: str, old: str, new: str) -> str:
    if old not in text:
        raise ValueError(f"Expected text not found:\n{old}")
    return text.replace(old, new, 1)


def main() -> None:
    text = SOURCE.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '    <matrix coldim="2" name="TEFLON_EFFICIENCY" values="2.25*eV 0.0 2.48*eV 0.0 2.76*eV 0.0 3.10*eV 0.0 3.54*eV 0.0"/>\n',
        '    <matrix coldim="2" name="TEFLON_EFFICIENCY" values="2.25*eV 0.0 2.48*eV 0.0 2.76*eV 0.0 3.10*eV 0.0 3.54*eV 0.0"/>\n'
        '    <matrix coldim="2" name="VANTA_BLACK_REFLECTIVITY" values="2.25*eV 0.01 2.48*eV 0.01 2.76*eV 0.01 3.10*eV 0.01 3.54*eV 0.01"/>\n'
        '    <matrix coldim="2" name="VANTA_BLACK_EFFICIENCY" values="2.25*eV 0.0 2.48*eV 0.0 2.76*eV 0.0 3.10*eV 0.0 3.54*eV 0.0"/>\n',
    )

    text = replace_once(
        text,
        '        <material name="Teflon" state="solid">\n'
        '            <D value="2.2" unit="g/cm3"/>\n'
        '            <composite n="2" ref="C"/>\n'
        '            <composite n="4" ref="F"/>\n'
        '        </material>\n',
        '        <material name="Teflon" state="solid">\n'
        '            <D value="2.2" unit="g/cm3"/>\n'
        '            <composite n="2" ref="C"/>\n'
        '            <composite n="4" ref="F"/>\n'
        '        </material>\n'
        '        <material name="VantaBlack" state="solid">\n'
        '            <D value="1.8" unit="g/cm3"/>\n'
        '            <composite n="1" ref="C"/>\n'
        '        </material>\n',
    )

    text = replace_once(
        text,
        '        <opticalsurface name="sipm_detection_surface" model="unified" finish="polished" type="dielectric_metal" value="1.0">\n',
        '        <opticalsurface name="black_absorber_surface" model="unified" finish="groundfrontpainted" type="dielectric_dielectric" value="1.0">\n'
        '            <property name="REFLECTIVITY" ref="VANTA_BLACK_REFLECTIVITY"/>\n'
        '            <property name="EFFICIENCY" ref="VANTA_BLACK_EFFICIENCY"/>\n'
        '        </opticalsurface>\n'
        '        <opticalsurface name="sipm_detection_surface" model="unified" finish="polished" type="dielectric_metal" value="1.0">\n',
    )

    text = replace_once(
        text,
        '        <volume name="teflon_x_side_wrap">\n'
        '            <materialref ref="Teflon"/>\n'
        '            <solidref ref="teflon_x_side_solid"/>\n'
        '            <auxiliary auxtype="Color" auxvalue="1 0.35 0.75"/>\n'
        '            <auxiliary auxtype="Transparency" auxvalue="0.85"/>\n'
        '        </volume>\n',
        '        <volume name="black_x_side_wrap">\n'
        '            <materialref ref="VantaBlack"/>\n'
        '            <solidref ref="teflon_x_side_solid"/>\n'
        '            <auxiliary auxtype="Color" auxvalue="0 0 0"/>\n'
        '            <auxiliary auxtype="Transparency" auxvalue="0.0"/>\n'
        '        </volume>\n',
    )
    text = replace_once(
        text,
        '        <volume name="teflon_z_side_wrap">\n'
        '            <materialref ref="Teflon"/>\n'
        '            <solidref ref="teflon_z_side_solid"/>\n'
        '            <auxiliary auxtype="Color" auxvalue="1 0.35 0.75"/>\n'
        '            <auxiliary auxtype="Transparency" auxvalue="0.85"/>\n'
        '        </volume>\n',
        '        <volume name="black_z_side_wrap">\n'
        '            <materialref ref="VantaBlack"/>\n'
        '            <solidref ref="teflon_z_side_solid"/>\n'
        '            <auxiliary auxtype="Color" auxvalue="0 0 0"/>\n'
        '            <auxiliary auxtype="Transparency" auxvalue="0.0"/>\n'
        '        </volume>\n',
    )

    text = text.replace('name="teflon_posx_phys"', 'name="black_posx_phys"')
    text = text.replace('name="teflon_negx_phys"', 'name="black_negx_phys"')
    text = text.replace('name="teflon_posz_phys"', 'name="black_posz_phys"')
    text = text.replace('name="teflon_negz_phys"', 'name="black_negz_phys"')
    text = text.replace('<volumeref ref="teflon_x_side_wrap"/>', '<volumeref ref="black_x_side_wrap"/>')
    text = text.replace('<volumeref ref="teflon_z_side_wrap"/>', '<volumeref ref="black_z_side_wrap"/>')

    text = text.replace('name="slab_to_teflon_posx" surfaceproperty="teflon_diffuse_surface"', 'name="slab_to_black_posx" surfaceproperty="black_absorber_surface"')
    text = text.replace('name="slab_to_teflon_negx" surfaceproperty="teflon_diffuse_surface"', 'name="slab_to_black_negx" surfaceproperty="black_absorber_surface"')
    text = text.replace('name="slab_to_teflon_posz" surfaceproperty="teflon_diffuse_surface"', 'name="slab_to_black_posz" surfaceproperty="black_absorber_surface"')
    text = text.replace('name="slab_to_teflon_negz" surfaceproperty="teflon_diffuse_surface"', 'name="slab_to_black_negz" surfaceproperty="black_absorber_surface"')
    text = text.replace('<physvolref ref="teflon_posx_phys"/>', '<physvolref ref="black_posx_phys"/>')
    text = text.replace('<physvolref ref="teflon_negx_phys"/>', '<physvolref ref="black_negx_phys"/>')
    text = text.replace('<physvolref ref="teflon_posz_phys"/>', '<physvolref ref="black_posz_phys"/>')
    text = text.replace('<physvolref ref="teflon_negz_phys"/>', '<physvolref ref="black_negz_phys"/>')

    text = text.replace('name="teflon_x_side_skin" surfaceproperty="teflon_diffuse_surface"', 'name="black_x_side_skin" surfaceproperty="black_absorber_surface"')
    text = text.replace('name="teflon_z_side_skin" surfaceproperty="teflon_diffuse_surface"', 'name="black_z_side_skin" surfaceproperty="black_absorber_surface"')
    text = text.replace('<volumeref ref="teflon_x_side_wrap"/>', '<volumeref ref="black_x_side_wrap"/>')
    text = text.replace('<volumeref ref="teflon_z_side_wrap"/>', '<volumeref ref="black_z_side_wrap"/>')

    OUT.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
