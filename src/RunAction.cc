#include "RunAction.hh"
#include "G4AnalysisManager.hh"
#include "G4Run.hh"

#include <iostream>
#include <fstream>

RunAction::RunAction(PrimaryGeneratorAction * aGenerator) : generator(aGenerator)
{   
    // Create a Default filename that can be changed by the user using UI commands
    G4String defaultFilename = "MUON";
    baseFilename = defaultFilename;

    RunAction::BookAnalysis(defaultFilename);
}

RunAction::~RunAction() = default;

void RunAction::BeginOfRunAction(const G4Run* run)
{
    // Print that you are staring a run
    if (isMaster) G4cout << ">>> Run " << run->GetRunID() << " starting..." << G4endl;

    auto analysisManager = G4AnalysisManager::Instance();
    analysisManager->SetFileName(BuildRunFilename(baseFilename, run->GetRunID()));
    analysisManager->OpenFile();
}

void RunAction::EndOfRunAction(const G4Run* run)
{
    auto analysisManager = G4AnalysisManager::Instance();
    analysisManager->Write();
    analysisManager->CloseFile();
#ifndef ADD_RADIOACTIVE
    if (!isMaster && generator != nullptr && generator->generator != nullptr) {
        G4double line = generator->generator->timeSimulated();
        std::ofstream outfile(BuildRunTimeFilename(baseFilename, run->GetRunID()));
        if (outfile.is_open()) {
            outfile << line << std::endl;
            outfile.close();
        }
    }
#endif
}

G4String RunAction::BuildRunFilename(const G4String& baseFilename, G4int runId)
{
    G4String filename = baseFilename;
    filename += "-run";
    filename += std::to_string(runId);
    return filename;
}

G4String RunAction::BuildRunTimeFilename(const G4String& baseFilename, G4int runId)
{
    G4String filename = BuildRunFilename(baseFilename, runId);
    filename += "-time.csv";
    return filename;
}

void RunAction::BookAnalysis(G4String filename, G4bool ntupleMerging){
    // Start the analysis manager
    auto analysisManager = G4AnalysisManager::Instance();
    analysisManager->SetVerboseLevel(0);

    analysisManager->SetDefaultFileType("csv");
    analysisManager->SetNtupleDirectoryName("output");
    analysisManager->SetFileName(filename);
    analysisManager->SetNtupleMerging(ntupleMerging);

    // Create the structure of the data as an Ntuple (Table)
    analysisManager->CreateNtuple("hits","TES Hits by Cosmic Rays");
    analysisManager->CreateNtupleIColumn("EventID");
    analysisManager->CreateNtupleIColumn("TrackID");
    analysisManager->CreateNtupleSColumn("Particle");
    analysisManager->CreateNtupleDColumn("EnergyDeposited");
    analysisManager->CreateNtupleDColumn("LocalTime");
    analysisManager->CreateNtupleSColumn("Volume");
    analysisManager->CreateNtupleDColumn("Copynumber");
    analysisManager->CreateNtupleDColumn("InitialEnergy");
    analysisManager->CreateNtupleSColumn("OriginVolume");
    analysisManager->CreateNtupleIColumn("ParentID");
    analysisManager->CreateNtupleSColumn("ProcessName");

    analysisManager->FinishNtuple();
}
