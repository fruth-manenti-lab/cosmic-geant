/************************
•     ┓             •    
┓┏┳┓┏┓┃┏┓┏┳┓┏┓┏┓╋┏┓╋┓┏┓┏┓
┗┛┗┗┣┛┗┗ ┛┗┗┗ ┛┗┗┗┻┗┗┗┛┛┗
    ┛                    
    Track Information

Stores the ID of the first generation migrant that created the track.
A migrant is a particle that was created outside of the sensitive volume and then has entered it, possibly creating secondary particles.
We want to separate them because a migrant entering a volume and depositing energy is what constitues a "count". This way in post sim
analysis we can group events by migrant id and add the energy deposited by daughter particles to the migrant particle. 
************************/

// The relevant headerfile
#include "TrackInformation.hh"

// Constructors
TrackInformation::TrackInformation(G4int id) : migrantID(id)
{}

TrackInformation::TrackInformation(G4String aProcessName) : processName(aProcessName)
{}

TrackInformation::TrackInformation(G4String aProcessName, G4String aSourceParticle)
    : processName(aProcessName), sourceParticle(aSourceParticle)
{}

//----------------------- 8< -------------[ cut here ]------------------------

// Destructor
TrackInformation::~TrackInformation()
{}

//----------------------- 8< -------------[ cut here ]------------------------

// Mutators
void            TrackInformation::SetMigrantID(G4int id)                  { this->migrantID = id;}
const G4int     TrackInformation::GetMigrantID()                          { return migrantID;}
void            TrackInformation::SetProcessName(G4String aProcessName)   { this->processName = aProcessName;}
const G4String  TrackInformation::GetProcessName()                        { return processName;}
void            TrackInformation::SetSourceParticle(G4String particle)    { this->sourceParticle = particle;}
const G4String  TrackInformation::GetSourceParticle()                     { return sourceParticle;}
