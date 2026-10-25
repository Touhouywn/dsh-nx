import NXOpen
import NXOpen.Features


def main():
    session = NXOpen.Session.GetSession()
    work_part = session.Parts.Work
    if work_part is None:
        session.ListingWindow.Open()
        session.ListingWindow.WriteLine("No work part is open. Create or open a part first.")
        return

    block_builder = work_part.Features.CreateBlockFeatureBuilder(None)
    origin = NXOpen.Point3d(0.0, 0.0, 0.0)
    block_builder.SetOriginAndLengths(origin, "100", "60", "30")
    block_builder.CommitFeature()
    block_builder.Destroy()
    work_part.Save(NXOpen.BasePart.SaveComponents.TrueValue, NXOpen.BasePart.CloseAfterSave.FalseValue)

    session.ListingWindow.Open()
    session.ListingWindow.WriteLine("Created demo block 100 x 60 x 30 mm.")


if __name__ == "__main__":
    main()
