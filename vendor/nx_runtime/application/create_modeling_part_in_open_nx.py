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


def main():
    session = NXOpen.Session.GetSession()

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    root = project_root()
    os.makedirs(root, exist_ok=True)
    part_path = os.path.join(
        root,
        "nx_in_open_window_modeling_%s.prt" % timestamp,
    )

    part = session.Parts.NewDisplay(part_path, NXOpen.Part.Units.Millimeters)
    session.Parts.SetWork(part)
    session.Parts.SetDisplay(part, False, False)
    session.ApplicationSwitchImmediate("UG_APP_MODELING")

    block_builder = part.Features.CreateBlockFeatureBuilder(None)
    block_builder.SetOriginAndLengths(NXOpen.Point3d(0.0, 0.0, 0.0), "80", "50", "25")
    block_builder.CommitFeature()
    block_builder.Destroy()

    part.ModelingViews.WorkView.Fit()
    part.Save(NXOpen.BasePart.SaveComponents.TrueValue, NXOpen.BasePart.CloseAfterSave.FalseValue)

    session.ListingWindow.Open()
    session.ListingWindow.WriteLine("Created in already open NX window: " + part_path)


if __name__ == "__main__":
    main()
