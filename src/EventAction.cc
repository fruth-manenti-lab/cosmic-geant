#include "EventAction.hh"
#include "G4TrajectoryContainer.hh"
#include "G4Event.hh"
#include "TESHit.hh"
#include "G4AnalysisManager.hh"
#include "G4SystemOfUnits.hh"

#ifdef ADD_SCAN
#include "ScanEventInfo.hh"
#endif

void EventAction::BeginOfEventAction(const G4Event* event)
{
    hitTES = false;
}

void EventAction::EndOfEventAction(const G4Event* event)
{

#ifdef FILTER_FOR_TES
    if (not hitTES) return; // when turned on it allows to keep only events that had a tes hit
#endif

    auto eventHitsCollections = event->GetHCofThisEvent();
    auto analysisManager = G4AnalysisManager::Instance();

#ifdef ADD_SCAN
    const auto* scanInfo = static_cast<const ScanEventInfo*>(event->GetUserInformation());
    if (scanInfo != nullptr) {
        const auto& sourcePosition = scanInfo->GetSourcePosition();
        analysisManager->FillNtupleIColumn(1, 0, event->GetEventID());
        analysisManager->FillNtupleIColumn(1, 1, scanInfo->GetSourceIndex());
        analysisManager->FillNtupleIColumn(1, 2, scanInfo->GetSourceCycle());
        analysisManager->FillNtupleDColumn(1, 3, sourcePosition.x() / cm);
        analysisManager->FillNtupleDColumn(1, 4, sourcePosition.y() / cm);
        analysisManager->FillNtupleDColumn(1, 5, sourcePosition.z() / cm);
        analysisManager->AddNtupleRow(1);
    }
#endif

    for (int i=0;i<eventHitsCollections->GetNumberOfCollections();i++){
        auto eventHitsCollection = static_cast<HitsCollection*> (eventHitsCollections->GetHC(i));

        for (int j=0;j<eventHitsCollection->GetSize();j++){
            TESHit* hit = (*eventHitsCollection)[j];
            
            analysisManager->FillNtupleIColumn(0, 0,event->GetEventID());
            analysisManager->FillNtupleIColumn(0, 1,hit->getTrackID());
            analysisManager->FillNtupleSColumn(0, 2,hit->getParticle());
            analysisManager->FillNtupleDColumn(0, 3,hit->getEnergyDeposited()/keV);
            analysisManager->FillNtupleDColumn(0, 4,hit->getPosition()[0]);
            analysisManager->FillNtupleDColumn(0, 5,hit->getPosition()[1]);
            analysisManager->FillNtupleDColumn(0, 6,hit->getPosition()[2]);
            analysisManager->FillNtupleDColumn(0, 7,hit->getTime()/ns);
            analysisManager->FillNtupleSColumn(0, 8,hit->getVolume());
            analysisManager->FillNtupleDColumn(0, 9,hit->getCopyNo());
            analysisManager->FillNtupleDColumn(0, 10,hit->getInitialEnergy()/keV);
            analysisManager->FillNtupleSColumn(0, 11,hit->getOrigin());
            analysisManager->FillNtupleIColumn(0, 12,hit->getParentID());
            analysisManager->FillNtupleSColumn(0, 13,hit->getProcessName());
            analysisManager->FillNtupleDColumn(0, 14,hit->getStepID());
#ifdef ADD_SCAN
            if (scanInfo != nullptr) {
                const auto& sourcePosition = scanInfo->GetSourcePosition();
                analysisManager->FillNtupleIColumn(0, 15, scanInfo->GetSourceIndex());
                analysisManager->FillNtupleIColumn(0, 16, scanInfo->GetSourceCycle());
                analysisManager->FillNtupleDColumn(0, 17, sourcePosition.x() / cm);
                analysisManager->FillNtupleDColumn(0, 18, sourcePosition.y() / cm);
                analysisManager->FillNtupleDColumn(0, 19, sourcePosition.z() / cm);
            }
#endif
#ifdef ADD_SOURCE_TAGGING
            analysisManager->FillNtupleSColumn(0, 15, hit->getSourceParticle());
#endif
            analysisManager->AddNtupleRow(0);
        }
    }
}
