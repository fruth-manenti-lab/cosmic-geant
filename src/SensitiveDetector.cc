#include "SensitiveDetector.hh"
#include "G4SDManager.hh"
#include "TrackInformation.hh"

SensitiveDetector::SensitiveDetector(const G4String& name, const G4String& hitsCollectionName, EventAction * anEventAction) : eventAction(anEventAction), G4VSensitiveDetector(name)
{
    collectionName.insert(hitsCollectionName);
}

SensitiveDetector::~SensitiveDetector()
{}

void SensitiveDetector::Initialize(G4HCofThisEvent* hitsCollection)
{
    this->hitsCollection = new HitsCollection(SensitiveDetectorName, collectionName[0]);

    G4int hitsCollectionId = G4SDManager::GetSDMpointer()->GetCollectionID(collectionName[0]);   
    hitsCollection->AddHitsCollection(hitsCollectionId,this->hitsCollection);
}

G4bool SensitiveDetector::ProcessHits(G4Step* step, G4TouchableHistory* history)
{
    G4double edep = step->GetTotalEnergyDeposit();
    G4String volume = step->GetPreStepPoint()->GetPhysicalVolume()->GetName();
    G4String particleName = step->GetTrack()->GetParticleDefinition()->GetParticleName();

    // if TES B or E are hit record it
    if (volume.find("B") != G4String::npos or volume.find("E") != G4String::npos){eventAction->SetHitTES(true);}

    // if(edep == 0.0) return false;
    G4String parentVolume = "NA";
    if (step->GetTrack()->GetOriginTouchable()){
        parentVolume = step->GetTrack()->GetOriginTouchable()->GetVolume()->GetName();
    }

    G4String processName = "Primary";
    if (step->GetTrack()->GetCreatorProcess())
    {
        processName = step->GetTrack()->GetCreatorProcess()->GetProcessName();
    }

    G4String sourceParticle = "unknown";
    if (auto* trackInfo = dynamic_cast<TrackInformation*>(step->GetTrack()->GetUserInformation()))
    {
        sourceParticle = trackInfo->GetSourceParticle();
    }
    if (sourceParticle.empty()) {
        sourceParticle = step->GetTrack()->GetParticleDefinition()->GetParticleName();
    }

    auto hit = new TESHit();
    hit->setTrackID(step->GetTrack()->GetTrackID());
    hit->setParticle(particleName);
    hit->setEnergyDeposited(edep);
    hit->setPosition(step->GetPostStepPoint()->GetPosition());
    hit->setTime(step->GetPostStepPoint()->GetLocalTime());
    hit->setVolume(step->GetPreStepPoint()->GetPhysicalVolume()->GetName());
    hit->setCopyNo(step->GetPreStepPoint()->GetTouchableHandle()->GetCopyNumber());
    hit->setInitialEnergy   (step->GetTrack()->GetVertexKineticEnergy());
    hit->setOrigin(parentVolume);
    hit->setParentID(step->GetTrack()->GetParentID());
    hit->setProcessName(processName);
    hit->setSourceParticle(sourceParticle);
    hit->setStepID(step->GetTrack()->GetCurrentStepNumber());

    hitsCollection->insert(hit);


    const G4bool isMuonClockMuon =
        volume == "muon_clock_phys" && (particleName == "mu+" || particleName == "mu-");
    if (!isMuonClockMuon)
    {
        step->GetTrack()->SetTrackStatus(fStopAndKill);
    }


    return true;
}

void SensitiveDetector::EndOfEvent(G4HCofThisEvent* hitsCollection){
    if ( verboseLevel>1 ) {
     G4int nofHits = this->hitsCollection->entries();
     G4cout << G4endl
            << "-------->Hits Collection: in this event they are " << nofHits
            << " hits in the tracker chambers: " << G4endl;
     for ( G4int i=0; i<nofHits; i++ ) (*(this->hitsCollection))[i]->Print();
  }
}
