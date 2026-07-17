#ifdef ADD_SCAN

#include "ScanMessenger.hh"

#include "G4UIcmdWithAString.hh"
#include "G4UIdirectory.hh"
#include "PrimaryGeneratorAction.hh"

ScanMessenger::ScanMessenger(PrimaryGeneratorAction* primaryGeneratorAction)
    : G4UImessenger(), primaryGenerator(primaryGeneratorAction)
{
    scanDir = new G4UIdirectory("/scan/");
    scanDir->SetGuidance("Muon scan source control");

    positionFileCmd = new G4UIcmdWithAString("/scan/positionFile", this);
    positionFileCmd->SetGuidance("Set macro/CSV file containing /gps/position rows for ADD_SCAN mode.");
    positionFileCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
}

ScanMessenger::~ScanMessenger()
{
    delete positionFileCmd;
    delete scanDir;
}

void ScanMessenger::SetNewValue(G4UIcommand* command, G4String newValue)
{
    if (command == positionFileCmd) {
        primaryGenerator->SetScanPositionFile(newValue);
    }
}

#endif
