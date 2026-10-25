import datetime
import os

import NXOpen
import NXOpen.Features


def project_root():
    return (
        os.environ.get("NX2512_PROJECT_ROOT")
        or os.environ.get("DC2512_PROJECT_ROOT")
        or os.path.join(os.environ.get("USERPROFILE", os.getcwd()), "Documents", "Codex", "NX2512")
    )


def visible_mark(session, name):
    return session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, name)


def name_object(obj, name):
    if obj is None:
        return obj
    try:
        obj.SetName(name)
    except Exception:
        try:
            obj.Name = name
        except Exception:
            pass
    return obj


def create_expression(part, name, formula, unit_type="Number"):
    try:
        expr = part.Expressions.CreateExpression(unit_type, "%s=%s" % (name, formula))
        name_object(expr, name)
        return expr
    except Exception:
        return None


def ensure_modeling_part(session, part_name):
    part = session.Parts.Work
    if part is not None:
        session.ApplicationSwitchImmediate("UG_APP_MODELING")
        return part

    root = project_root()
    os.makedirs(root, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    part_path = os.path.join(root, "%s_%s.prt" % (part_name, timestamp))
    part = session.Parts.NewDisplay(part_path, NXOpen.Part.Units.Millimeters)
    session.Parts.SetWork(part)
    session.Parts.SetDisplay(part, False, False)
    session.ApplicationSwitchImmediate("UG_APP_MODELING")
    return part


def create_named_block(part, step_name, origin, length_formula, width_formula, height_formula):
    builder = part.Features.CreateBlockFeatureBuilder(None)
    builder.SetOriginAndLengths(
        NXOpen.Point3d(float(origin[0]), float(origin[1]), float(origin[2])),
        str(length_formula),
        str(width_formula),
        str(height_formula),
    )
    feature = builder.CommitFeature()
    name_object(feature, step_name)
    builder.Destroy()
    return feature


def main():
    session = NXOpen.Session.GetSession()
    listing = session.ListingWindow
    listing.Open()

    part = ensure_modeling_part(session, "history_feature_demo")

    visible_mark(session, "01 Define editable expressions")
    create_expression(part, "base_length", "100")
    create_expression(part, "base_width", "60")
    create_expression(part, "base_height", "30")

    visible_mark(session, "02 Create named base feature")
    create_named_block(
        part,
        "02_Base_Block",
        origin=(0.0, 0.0, 0.0),
        length_formula="base_length",
        width_formula="base_width",
        height_formula="base_height",
    )

    # Add later stages as separate visible marks and named features:
    # 03_Profile_Sketch, 04_Main_Extrude, 05_Hole_Feature, 06_Hole_Pattern,
    # 07_Chamfers, 08_Edge_Fillets, 09_Final_Check.

    part.ModelingViews.WorkView.Fit()
    part.Save(NXOpen.BasePart.SaveComponents.TrueValue, NXOpen.BasePart.CloseAfterSave.FalseValue)
    listing.WriteLine("Created history-preserving feature demo with named Part Navigator steps.")


if __name__ == "__main__":
    main()
