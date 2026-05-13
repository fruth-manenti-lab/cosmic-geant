#!/usr/bin/env python3
"""Generate the hybrid 16 face-mount + 16 fiber-end SiPM GDML."""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "faceMountGeometry_1m_diagonal_sipms.gdml"
OUT = ROOT / "faceMountGeometry_1m_hybrid_16face_16fiber.gdml"

FACE_CENTERS = [-375.0, -125.0, 125.0, 375.0]
PLUS_Z_INDICES = [0, 4, 8, 12]
MINUS_Z_INDICES = [2, 6, 10, 14]
PLUS_X_INDICES = [0, 4, 8, 12]
MINUS_X_INDICES = [2, 6, 10, 14]


def indent(text: str, spaces: int = 8) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line else "" for line in text.splitlines())


def build_face_variables() -> str:
    rows = []
    sipm_id = 0
    for z in FACE_CENTERS:
        for x in FACE_CENTERS:
            rows.append(f'    <variable name="sipm{sipm_id}_x" value="{x:.6f}"/>')
            rows.append(f'    <variable name="sipm{sipm_id}_z" value="{z:.6f}"/>')
            sipm_id += 1
    return "\n".join(rows)


def build_top_teflon_steps() -> str:
    rows = []
    for idx in range(16):
        first = "teflon_top_base" if idx == 0 else f"teflon_top_step_{idx - 1}"
        rows.append(
            f'''        <subtraction name="teflon_top_step_{idx}">
            <first ref="{first}"/>
            <second ref="face_teflon_hole"/>
            <position x="sipm{idx}_x" y="0" z="sipm{idx}_z" unit="mm"/>
        </subtraction>'''
        )
    return "\n".join(rows)


def side_steps(axis: str, sign: str, indices: list[int]) -> str:
    if axis == "z":
        base = "teflon_z_side_base"
        hole = "teflon_z_fiber_hole"
        coord = "x"
        other = "z"
    else:
        base = "teflon_x_side_base"
        hole = "teflon_x_fiber_hole"
        coord = "z"
        other = "x"

    rows = []
    for step, lane_index in enumerate(indices):
        first = base if step == 0 else f"teflon_{sign}{axis}_side_step_{step - 1}"
        if axis == "z":
            position = (
                f'<position x="lane_start + {lane_index}*lane_pitch" '
                f'y="groove_bottom_y" z="0" unit="mm"/>'
            )
        else:
            # +x/-x row numbering is top-to-bottom, so index 0 is lane 15.
            lane_expr = f"lane_start + (15-{lane_index})*lane_pitch"
            position = (
                f'<position x="0" y="groove_top_y" z="{lane_expr}" unit="mm"/>'
            )
        rows.append(
            f'''        <subtraction name="teflon_{sign}{axis}_side_step_{step}">
            <first ref="{first}"/>
            <second ref="{hole}"/>
            {position}
        </subtraction>'''
        )
    return "\n".join(rows)


def groove_physvols() -> str:
    rows = []
    for lane_index in sorted(set(PLUS_Z_INDICES + MINUS_Z_INDICES)):
        rows.append(
            f'''                <physvol name="groove_z_{lane_index}_phys">
                    <volumeref ref="groove_z"/>
                    <position x="lane_start + {lane_index}*lane_pitch" y="groove_bottom_y" z="0" unit="mm"/>
                </physvol>'''
        )
    for row_index in sorted(set(PLUS_X_INDICES + MINUS_X_INDICES)):
        lane_index = 15 - row_index
        rows.append(
            f'''                <physvol name="groove_x_row_{row_index}_phys">
                    <volumeref ref="groove_x"/>
                    <position x="0" y="groove_top_y" z="lane_start + {lane_index}*lane_pitch" unit="mm"/>
                </physvol>'''
        )
    return "\n".join(rows)


def face_sipm_physvols() -> str:
    rows = []
    for idx in range(16):
        rows.append(
            f'''            <physvol name="face_grease_{idx}_phys" copynumber="{1000 + idx}">
                <volumeref ref="face_grease"/>
                <position x="sipm{idx}_x" z="sipm{idx}_z" y="grease_y" unit="mm"/>
                <rotationref ref="sipmrot"/>
            </physvol>
            <physvol name="face_sipm_{idx}_phys" copynumber="{idx}">
                <volumeref ref="face_sipm"/>
                <position x="sipm{idx}_x" z="sipm{idx}_z" y="sipm_y" unit="mm"/>
                <rotationref ref="sipmrot"/>
            </physvol>'''
        )
    return "\n".join(rows)


def fiber_sipm_physvols() -> str:
    rows = []
    copy_no = 100
    grease_no = 1100
    for lane_index in PLUS_Z_INDICES:
        x_expr = f"lane_start + {lane_index}*lane_pitch"
        rows.append(
            f'''            <physvol name="fiber_grease_pz_{lane_index}_phys" copynumber="{grease_no}">
                <volumeref ref="fiber_grease"/>
                <position x="{x_expr}" y="groove_bottom_y" z="fiber_grease_pos_z" unit="mm"/>
                <rotationref ref="sipm_to_z"/>
            </physvol>
            <physvol name="fiber_sipm_pz_{lane_index}_phys" copynumber="{copy_no}">
                <file name="./geometry/sipm1.gdml"/>
                <position x="{x_expr}" y="groove_bottom_y" z="fiber_sipm_pos_z" unit="mm"/>
                <rotationref ref="sipm_to_z"/>
            </physvol>'''
        )
        copy_no += 1
        grease_no += 1
    for lane_index in MINUS_Z_INDICES:
        x_expr = f"lane_start + {lane_index}*lane_pitch"
        rows.append(
            f'''            <physvol name="fiber_grease_nz_{lane_index}_phys" copynumber="{grease_no}">
                <volumeref ref="fiber_grease"/>
                <position x="{x_expr}" y="groove_bottom_y" z="fiber_grease_neg_z" unit="mm"/>
                <rotationref ref="sipm_to_z"/>
            </physvol>
            <physvol name="fiber_sipm_nz_{lane_index}_phys" copynumber="{copy_no}">
                <file name="./geometry/sipm1.gdml"/>
                <position x="{x_expr}" y="groove_bottom_y" z="fiber_sipm_neg_z" unit="mm"/>
                <rotationref ref="sipm_to_z"/>
            </physvol>'''
        )
        copy_no += 1
        grease_no += 1
    for row_index in PLUS_X_INDICES:
        z_expr = f"lane_start + (15-{row_index})*lane_pitch"
        rows.append(
            f'''            <physvol name="fiber_grease_px_row_{row_index}_phys" copynumber="{grease_no}">
                <volumeref ref="fiber_grease"/>
                <position x="fiber_grease_pos_x" y="groove_top_y" z="{z_expr}" unit="mm"/>
                <rotationref ref="sipm_to_x"/>
            </physvol>
            <physvol name="fiber_sipm_px_row_{row_index}_phys" copynumber="{copy_no}">
                <file name="./geometry/sipm1.gdml"/>
                <position x="fiber_sipm_pos_x" y="groove_top_y" z="{z_expr}" unit="mm"/>
                <rotationref ref="sipm_to_x"/>
            </physvol>'''
        )
        copy_no += 1
        grease_no += 1
    for row_index in MINUS_X_INDICES:
        z_expr = f"lane_start + (15-{row_index})*lane_pitch"
        rows.append(
            f'''            <physvol name="fiber_grease_nx_row_{row_index}_phys" copynumber="{grease_no}">
                <volumeref ref="fiber_grease"/>
                <position x="fiber_grease_neg_x" y="groove_top_y" z="{z_expr}" unit="mm"/>
                <rotationref ref="sipm_to_x"/>
            </physvol>
            <physvol name="fiber_sipm_nx_row_{row_index}_phys" copynumber="{copy_no}">
                <file name="./geometry/sipm1.gdml"/>
                <position x="fiber_sipm_neg_x" y="groove_top_y" z="{z_expr}" unit="mm"/>
                <rotationref ref="sipm_to_x"/>
            </physvol>'''
        )
        copy_no += 1
        grease_no += 1
    return "\n".join(rows)


def build_solids(optical_surfaces: str) -> str:
    return f'''    <solids>
        <box lunit="m" name="world_solid" x="2" y="2" z="2" />
        <box lunit="cm" name="detector_solid" x="110" y="200" z="110" />
        <box name="scintillator_slab_solid" x="1000" y="20" z="1000" lunit="mm" />
        <box name="groove_z_solid" x="1.2" y="1.2" z="1000" lunit="mm" />
        <box name="groove_x_solid" x="1000" y="1.2" z="1.2" lunit="mm" />
        <box name="face_grease_solid" x="grease_size" y="0.1" z="grease_size" lunit="mm" />
        <box name="fiber_grease_solid" x="1.0" y="0.1" z="1.0" lunit="mm" />
        <box name="face_sipm_solid" x="sipm_size" y="1" z="sipm_size" lunit="mm" />
        <box name="teflon_top_base" x="1000" y="2*teflon_half_thickness" z="1000" lunit="mm" />
        <box name="teflon_bottom_solid" x="1000" y="2*teflon_half_thickness" z="1000" lunit="mm" />
        <box name="teflon_x_side_base" x="2*teflon_half_thickness" y="20" z="1000" lunit="mm" />
        <box name="teflon_z_side_base" x="1000" y="20" z="2*teflon_half_thickness" lunit="mm" />
        <box name="face_teflon_hole" x="teflon_hole_size" y="teflon_hole_y" z="teflon_hole_size" lunit="mm" />
        <box name="teflon_x_fiber_hole" x="teflon_hole_y" y="1.4" z="1.4" lunit="mm" />
        <box name="teflon_z_fiber_hole" x="1.4" y="1.4" z="teflon_hole_y" lunit="mm" />
{build_top_teflon_steps()}
{side_steps("z", "pos", PLUS_Z_INDICES)}
{side_steps("z", "neg", MINUS_Z_INDICES)}
{side_steps("x", "pos", PLUS_X_INDICES)}
{side_steps("x", "neg", MINUS_X_INDICES)}
{optical_surfaces}
    </solids>'''


def build_structure() -> str:
    return f'''    <structure>
        <volume name="groove_z">
            <materialref ref="OpticalGrease"/>
            <solidref ref="groove_z_solid"/>
            <auxiliary auxtype="Color" auxvalue="0.6 0.9 1.0"/>
            <auxiliary auxtype="Transparency" auxvalue="0.1"/>
            <physvol>
                <file name="./geometry/fiber_kuraray_embedded.gdml"/>
            </physvol>
        </volume>

        <volume name="groove_x">
            <materialref ref="OpticalGrease"/>
            <solidref ref="groove_x_solid"/>
            <auxiliary auxtype="Color" auxvalue="0.6 0.9 1.0"/>
            <auxiliary auxtype="Transparency" auxvalue="0.1"/>
            <physvol>
                <file name="./geometry/fiber_kuraray_embedded.gdml"/>
                <rotationref ref="fiber_to_x"/>
            </physvol>
        </volume>

        <volume name="face_sipm">
            <materialref ref="SiMat"/>
            <solidref ref="face_sipm_solid"/>
            <auxiliary auxtype="Color" auxvalue="1 0 0"/>
            <auxiliary auxtype="SensDet"/>
        </volume>

        <volume name="face_grease">
            <materialref ref="OpticalGrease"/>
            <solidref ref="face_grease_solid"/>
            <auxiliary auxtype="Color" auxvalue="0 0.35 1"/>
            <auxiliary auxtype="Transparency" auxvalue="0.2"/>
        </volume>

        <volume name="fiber_grease">
            <materialref ref="OpticalGrease"/>
            <solidref ref="fiber_grease_solid"/>
            <auxiliary auxtype="Color" auxvalue="0 0.35 1"/>
            <auxiliary auxtype="Transparency" auxvalue="0.2"/>
        </volume>

        <volume name="scintillator_slab">
            <materialref ref="PVT"/>
            <solidref ref="scintillator_slab_solid"/>
            <auxiliary auxtype="Color" auxvalue="1 1 1"/>
            <auxiliary auxtype="Transparency" auxvalue="0.5"/>
{groove_physvols()}
        </volume>

        <volume name="teflon_top_wrap">
            <materialref ref="Teflon"/>
            <solidref ref="teflon_top_step_15"/>
            <auxiliary auxtype="Color" auxvalue="1 0.35 0.75"/>
            <auxiliary auxtype="Transparency" auxvalue="0.85"/>
        </volume>

        <volume name="teflon_bottom_wrap">
            <materialref ref="Teflon"/>
            <solidref ref="teflon_bottom_solid"/>
            <auxiliary auxtype="Color" auxvalue="1 0.35 0.75"/>
            <auxiliary auxtype="Transparency" auxvalue="0.85"/>
        </volume>

        <volume name="teflon_posx_wrap"><materialref ref="Teflon"/><solidref ref="teflon_posx_side_step_3"/><auxiliary auxtype="Color" auxvalue="1 0.35 0.75"/><auxiliary auxtype="Transparency" auxvalue="0.85"/></volume>
        <volume name="teflon_negx_wrap"><materialref ref="Teflon"/><solidref ref="teflon_negx_side_step_3"/><auxiliary auxtype="Color" auxvalue="1 0.35 0.75"/><auxiliary auxtype="Transparency" auxvalue="0.85"/></volume>
        <volume name="teflon_posz_wrap"><materialref ref="Teflon"/><solidref ref="teflon_posz_side_step_3"/><auxiliary auxtype="Color" auxvalue="1 0.35 0.75"/><auxiliary auxtype="Transparency" auxvalue="0.85"/></volume>
        <volume name="teflon_negz_wrap"><materialref ref="Teflon"/><solidref ref="teflon_negz_side_step_3"/><auxiliary auxtype="Color" auxvalue="1 0.35 0.75"/><auxiliary auxtype="Transparency" auxvalue="0.85"/></volume>

        <volume name="detector_logical">
            <materialref ref="Air"/>
            <solidref ref="detector_solid"/>
            <physvol><positionref ref="roofpos"/><file name="./geometry/roof.gdml"/></physvol>
            <physvol name="slab_phys"><positionref ref="scintillator1pos"/><volumeref ref="scintillator_slab"/></physvol>
            <physvol name="teflon_top_phys"><volumeref ref="teflon_top_wrap"/><position x="0" y="teflon_top_y" z="0" unit="mm"/></physvol>
            <physvol name="teflon_bottom_phys"><volumeref ref="teflon_bottom_wrap"/><position x="0" y="teflon_bottom_y" z="0" unit="mm"/></physvol>
            <physvol name="teflon_posx_phys"><volumeref ref="teflon_posx_wrap"/><position x="teflon_side_x" y="0" z="0" unit="mm"/></physvol>
            <physvol name="teflon_negx_phys"><volumeref ref="teflon_negx_wrap"/><position x="-teflon_side_x" y="0" z="0" unit="mm"/></physvol>
            <physvol name="teflon_posz_phys"><volumeref ref="teflon_posz_wrap"/><position x="0" y="0" z="teflon_side_z" unit="mm"/></physvol>
            <physvol name="teflon_negz_phys"><volumeref ref="teflon_negz_wrap"/><position x="0" y="0" z="-teflon_side_z" unit="mm"/></physvol>
{face_sipm_physvols()}
{fiber_sipm_physvols()}
        </volume>

        <bordersurface name="slab_to_teflon_top" surfaceproperty="teflon_diffuse_surface"><physvolref ref="slab_phys"/><physvolref ref="teflon_top_phys"/></bordersurface>
        <bordersurface name="slab_to_teflon_bottom" surfaceproperty="teflon_diffuse_surface"><physvolref ref="slab_phys"/><physvolref ref="teflon_bottom_phys"/></bordersurface>
        <bordersurface name="slab_to_teflon_posx" surfaceproperty="teflon_diffuse_surface"><physvolref ref="slab_phys"/><physvolref ref="teflon_posx_phys"/></bordersurface>
        <bordersurface name="slab_to_teflon_negx" surfaceproperty="teflon_diffuse_surface"><physvolref ref="slab_phys"/><physvolref ref="teflon_negx_phys"/></bordersurface>
        <bordersurface name="slab_to_teflon_posz" surfaceproperty="teflon_diffuse_surface"><physvolref ref="slab_phys"/><physvolref ref="teflon_posz_phys"/></bordersurface>
        <bordersurface name="slab_to_teflon_negz" surfaceproperty="teflon_diffuse_surface"><physvolref ref="slab_phys"/><physvolref ref="teflon_negz_phys"/></bordersurface>

        <skinsurface name="slab_skin" surfaceproperty="clear_interface_surface"><volumeref ref="scintillator_slab"/></skinsurface>
        <skinsurface name="groove_z_skin" surfaceproperty="clear_interface_surface"><volumeref ref="groove_z"/></skinsurface>
        <skinsurface name="groove_x_skin" surfaceproperty="clear_interface_surface"><volumeref ref="groove_x"/></skinsurface>
        <skinsurface name="face_grease_skin" surfaceproperty="clear_interface_surface"><volumeref ref="face_grease"/></skinsurface>
        <skinsurface name="fiber_grease_skin" surfaceproperty="clear_interface_surface"><volumeref ref="fiber_grease"/></skinsurface>
        <skinsurface name="face_sipm_skin" surfaceproperty="sipm_detection_surface"><volumeref ref="face_sipm"/></skinsurface>
        <skinsurface name="teflon_top_skin" surfaceproperty="teflon_diffuse_surface"><volumeref ref="teflon_top_wrap"/></skinsurface>
        <skinsurface name="teflon_bottom_skin" surfaceproperty="teflon_diffuse_surface"><volumeref ref="teflon_bottom_wrap"/></skinsurface>
        <skinsurface name="teflon_posx_skin" surfaceproperty="teflon_diffuse_surface"><volumeref ref="teflon_posx_wrap"/></skinsurface>
        <skinsurface name="teflon_negx_skin" surfaceproperty="teflon_diffuse_surface"><volumeref ref="teflon_negx_wrap"/></skinsurface>
        <skinsurface name="teflon_posz_skin" surfaceproperty="teflon_diffuse_surface"><volumeref ref="teflon_posz_wrap"/></skinsurface>
        <skinsurface name="teflon_negz_skin" surfaceproperty="teflon_diffuse_surface"><volumeref ref="teflon_negz_wrap"/></skinsurface>

        <volume name="world_volume">
            <materialref ref="Air"/>
            <solidref ref="world_solid"/>
            <physvol><volumeref ref="detector_logical"/></physvol>
        </volume>
    </structure>

    <setup name="Default" version="1.0">
        <world ref="world_volume"/>
    </setup>
</gdml>
'''


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    prefix = source[: source.index("    <solids>")]
    prefix = prefix.replace(
        "    <rotation name=\"sipmrot\" x='0' unit='deg'/>",
        "    <rotation name=\"sipmrot\" x='0' unit='deg'/>\n"
        "    <rotation name=\"sipm_to_z\" x=\"90\" unit=\"deg\"/>\n"
        "    <rotation name=\"sipm_to_x\" z=\"90\" unit=\"deg\"/>\n"
        "    <rotation name=\"fiber_to_x\" y=\"90\" unit=\"deg\"/>",
    )
    prefix = re.sub(
        r"    <variable name=\"sipm0_x\".*?    <variable name=\"sipm31_z\" value=\"[^\"]+\"/>\n",
        build_face_variables() + "\n",
        prefix,
        flags=re.S,
    )
    insert_after = '    <variable name="teflon_side_z" value="500+teflon_half_thickness"/>\n'
    extra_vars = '''    <variable name="lane_start" value="-468.75"/>
    <variable name="lane_pitch" value="62.5"/>
    <variable name="groove_half_y" value="0.6"/>
    <variable name="groove_bottom_y" value="-slab_half_y+groove_half_y"/>
    <variable name="groove_top_y" value="slab_half_y-groove_half_y"/>
    <variable name="fiber_grease_pos_z" value="500+0.05"/>
    <variable name="fiber_grease_neg_z" value="-500-0.05"/>
    <variable name="fiber_sipm_pos_z" value="500+0.1+0.25"/>
    <variable name="fiber_sipm_neg_z" value="-500-0.1-0.25"/>
    <variable name="fiber_grease_pos_x" value="500+0.05"/>
    <variable name="fiber_grease_neg_x" value="-500-0.05"/>
    <variable name="fiber_sipm_pos_x" value="500+0.1+0.25"/>
    <variable name="fiber_sipm_neg_x" value="-500-0.1-0.25"/>
'''
    prefix = prefix.replace(insert_after, insert_after + extra_vars)
    optical_start = source.index("<!--           BLOCKING OPT SURFACE")
    optical_end = source.index("    </solids>", optical_start)
    optical_surfaces = source[optical_start:optical_end].rstrip()
    output = prefix + build_solids(optical_surfaces) + "\n\n" + build_structure()
    OUT.write_text(output, encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
