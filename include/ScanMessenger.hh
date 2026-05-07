#ifndef ScanMessenger_HH
#define ScanMessenger_HH

#include "G4UImessenger.hh"
#include "globals.hh"

class G4UIdirectory;
class G4UIcmdWithAString;
class PrimaryGeneratorAction;

class ScanMessenger : public G4UImessenger
{
    public:
        explicit ScanMessenger(PrimaryGeneratorAction* primaryGeneratorAction);
        ~ScanMessenger() override;

        void SetNewValue(G4UIcommand* command, G4String newValue) override;

    private:
        PrimaryGeneratorAction* primaryGenerator = nullptr;
        G4UIdirectory* scanDir = nullptr;
        G4UIcmdWithAString* positionFileCmd = nullptr;
};

#endif
