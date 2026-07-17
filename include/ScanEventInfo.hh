#ifndef ScanEventInfo_HH
#define ScanEventInfo_HH

#include "G4ThreeVector.hh"
#include "G4VUserEventInformation.hh"
#include "globals.hh"

class ScanEventInfo : public G4VUserEventInformation
{
    public:
        ScanEventInfo(G4int sourceIndex, G4int sourceCycle, const G4ThreeVector& sourcePosition)
            : index(sourceIndex), cycle(sourceCycle), position(sourcePosition) {}

        ~ScanEventInfo() override = default;

        G4int GetSourceIndex() const { return index; }
        G4int GetSourceCycle() const { return cycle; }
        const G4ThreeVector& GetSourcePosition() const { return position; }

        void Print() const override {}

    private:
        G4int index = -1;
        G4int cycle = -1;
        G4ThreeVector position;
};

#endif
