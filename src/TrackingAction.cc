/************************
•     ┓             •    
┓┏┳┓┏┓┃┏┓┏┳┓┏┓┏┓╋┏┓╋┓┏┓┏┓
┗┛┗┗┣┛┗┗ ┛┗┗┗ ┛┗┗┗┻┗┗┗┛┛┗
    ┛                    
     Tracking Action

Used to stop tracks that 
we don't want to simulate
from generating
************************/

// The relevant header
#include "TrackingAction.hh"

// Other Useful headers
#include "G4Track.hh"
#include "G4ParticleDefinition.hh"
#include "G4TrackingManager.hh"
#include "TrackInformation.hh"
#include "G4TrackVector.hh"


// Constructor
TrackingAction::TrackingAction() : G4UserTrackingAction()
{}

//----------------------- 8< -------------[ cut here ]------------------------

// Destructor
TrackingAction::~TrackingAction()
{}

//----------------------- 8< -------------[ cut here ]------------------------

// What to do before the track is generated
void TrackingAction::PreUserTrackingAction(const G4Track* track)
{
#ifdef ADD_SOURCE_TAGGING
    if (track->GetParentID() == 0 && track->GetUserInformation() == nullptr) {
        G4Track* tr = (G4Track*) track;
        tr->SetUserInformation(new TrackInformation("Primary", track->GetDefinition()->GetParticleName()));
    }
#endif

    // Get the particle this track is about
    G4ParticleDefinition* particle = track->GetDefinition();

    // If the particle is an ion
    if (particle->GetPDGCharge() > 2.){
        G4Track* tr = (G4Track*) track;

        // and it isn't the original atom
        if (track->GetTrackID() > 50){
            // Kill that track
            tr->SetTrackStatus(fStopAndKill);
        }
        else {
            tr->SetKineticEnergy(0.);
            tr->SetTrackStatus(fStopButAlive);

        }
    }
}

//----------------------- 8< -------------[ cut here ]------------------------

// What to do after the track is generated
void TrackingAction::PostUserTrackingAction(const G4Track* track)
{
#ifdef ADD_SOURCE_TAGGING
    G4String sourceParticle = "";
    if (auto* parentInfo = dynamic_cast<TrackInformation*>(track->GetUserInformation())) {
        sourceParticle = parentInfo->GetSourceParticle();
    }
    if (sourceParticle.empty()) {
        sourceParticle = track->GetDefinition()->GetParticleName();
    }
#endif

    // Get the current track's volume
    G4String volume = "NA";
    if (track->GetOriginTouchable())
    {
        volume = track->GetOriginTouchable()->GetVolume()->GetName();
    }

    // Get the children of this track
    G4TrackVector* children = fpTrackingManager->GimmeSecondaries();

    // If there are no children do nothing
    if (not children) return; 

    // Get their number
    size_t numberOfChilder = (*children).size();

    // For all children
    for (size_t i=0; i < numberOfChilder; i++)
    {
        // Get Child
        G4Track* child = (*children)[i];

        // If the child does not have an origin volume skip
        if (!child->GetVolume()) continue;
    
#ifdef ADD_SOURCE_TAGGING
        if (child->GetUserInformation() == nullptr) {
            G4String processName = "unknown";
            if (child->GetCreatorProcess()) {
                processName = child->GetCreatorProcess()->GetProcessName();
            }
            child->SetUserInformation(new TrackInformation(processName, sourceParticle));
        }
#endif

    }

    
}
