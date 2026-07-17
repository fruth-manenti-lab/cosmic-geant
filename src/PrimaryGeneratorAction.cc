#ifdef ADD_RADIOACTIVE

#include "PrimaryGeneratorAction.hh"

PrimaryGeneratorAction::PrimaryGeneratorAction(const char* filename)
{
    particleGun = new G4GeneralParticleSource();
}

PrimaryGeneratorAction::~PrimaryGeneratorAction()
{
    delete particleGun;
}

void PrimaryGeneratorAction::GeneratePrimaries(G4Event* anEvent)
{
    particleGun->GeneratePrimaryVertex(anEvent);
}


#elif defined(ADD_SCAN)

#include "PrimaryGeneratorAction.hh"
#include "ScanEventInfo.hh"
#include "ScanMessenger.hh"

#include "G4Exception.hh"
#include "G4SystemOfUnits.hh"

#include <cstdlib>
#include <fstream>
#include <sstream>
#include <vector>

PrimaryGeneratorAction::PrimaryGeneratorAction(const char* filename)
{
	particleGun = new G4ParticleGun(1);
	particleTable = G4ParticleTable::GetParticleTable();
	particleGun->SetParticleDefinition(particleTable->FindParticle("mu-"));
	particleGun->SetParticleEnergy(1000.0 * MeV);
	particleGun->SetParticleMomentumDirection(G4ThreeVector(0.0, -1.0, 0.0));
	particleGun->SetParticleTime(0.0);

	scanPositionFile = ResolveScanPositionFile(filename);
	scanMessenger = new ScanMessenger(this);
}

PrimaryGeneratorAction::~PrimaryGeneratorAction()
{
	delete particleGun;
	delete scanMessenger;
}

G4String PrimaryGeneratorAction::ResolveScanPositionFile(const char* filename) const
{
	if (filename != nullptr && *filename != 0) {
		return G4String(filename);
	}

	const char* envPath = std::getenv("MUON_SCAN_POSITION_FILE");
	if (envPath != nullptr && *envPath != 0) {
		return G4String(envPath);
	}

	const std::vector<G4String> candidates = {
		"macros/muon_scan_10events.mac",
		"../macros/muon_scan_10events.mac",
		"../../macros/muon_scan_10events.mac"
	};

	for (const auto& candidate : candidates) {
		std::ifstream probe(candidate);
		if (probe.good()) {
			return candidate;
		}
	}

	return candidates.front();
}

void PrimaryGeneratorAction::SetScanPositionFile(const G4String& path)
{
	scanPositionFile = path;
	scanPositionsLoaded = false;
	scanPositions.clear();
	G4cout << "PrimaryGeneratorAction: scan position file set to "
	       << scanPositionFile << G4endl;
}

void PrimaryGeneratorAction::LoadScanPositions(const G4String& path)
{
	scanPositions.clear();

	std::ifstream file(path);
	if (!file.is_open()) {
		G4String message = "Could not open scan position file: ";
		message += path;
		G4Exception("PrimaryGeneratorAction", "ScanPositionFileMissing", FatalException, message);
	}

	G4String line;
	while (std::getline(file, line)) {
		std::istringstream stream(line);
		std::string command;
		stream >> command;
		if (command != "/gps/position") {
			continue;
		}

		G4double x = 0.0;
		G4double y = 0.0;
		G4double z = 0.0;
		std::string unit = "cm";
		stream >> x >> y >> z >> unit;

		G4double scale = cm;
		if (unit == "mm") {
			scale = mm;
		} else if (unit == "m") {
			scale = m;
		} else if (unit != "cm") {
			G4String message = "Unsupported scan position unit in ";
			message += path;
			message += ": ";
			message += unit;
			G4Exception("PrimaryGeneratorAction", "ScanPositionUnit", FatalException, message);
		}

		ScanPosition scanPosition;
		scanPosition.index = static_cast<G4int>(scanPositions.size());
		scanPosition.position = G4ThreeVector(x * scale, y * scale, z * scale);
		scanPositions.push_back(scanPosition);
	}

	if (scanPositions.empty()) {
		G4String message = "No /gps/position rows found in scan position file: ";
		message += path;
		G4Exception("PrimaryGeneratorAction", "ScanPositionFileEmpty", FatalException, message);
	}

	G4cout << "PrimaryGeneratorAction: loaded " << scanPositions.size()
	       << " scan positions from " << path << G4endl;
	scanPositionsLoaded = true;
}

void PrimaryGeneratorAction::GeneratePrimaries(G4Event* anEvent)
{
	if (!scanPositionsLoaded) {
		LoadScanPositions(scanPositionFile);
	}

	const G4int eventId = anEvent->GetEventID();
	const G4int sourceIndex = eventId % static_cast<G4int>(scanPositions.size());
	const G4int sourceCycle = eventId / static_cast<G4int>(scanPositions.size());
	const auto& source = scanPositions[sourceIndex];

	particleGun->SetParticlePosition(source.position);
	anEvent->SetUserInformation(new ScanEventInfo(source.index, sourceCycle, source.position));
	particleGun->GeneratePrimaryVertex(anEvent);
}


#else

#include "PrimaryGeneratorAction.hh"
#include "Randomize.hh"
#include <iomanip>


PrimaryGeneratorAction::PrimaryGeneratorAction(const char* filename)
{
	// Define the particle gun
	particleGun = new G4ParticleGun();

	// Start CRYing
	std::ifstream file;
	file.open(filename,std::ios::in);
	char buffer[1000];

	// Handle the failure
	if (file.fail()){
		if (*filename != 0) G4cout << "PrimaryGeneratorAction: Failed to open CRY input file= " << filename << G4endl;
    	inputState=-1;
	} else {
		std::string setupString("");
		while(!file.getline(buffer,1000).eof()) {
			setupString.append(buffer);
			setupString.append(" ");
		}

		CRYSetup* setup  = new CRYSetup(setupString,"../data");
		generator = new CRYGenerator(setup);

		// set randim number generator
		RNGWrapper<CLHEP::HepRandomEngine>::set(CLHEP::HepRandom::getTheEngine(),&CLHEP::HepRandomEngine::flat);
		setup->setRandomFunction(RNGWrapper<CLHEP::HepRandomEngine>::rng);
		inputState=0;
	}

	// Store the cry particle properties
	vect = new std::vector<CRYParticle*>;

	// All particles in the simulation
	particleTable = G4ParticleTable::GetParticleTable();

	// Create the messenger
	particleMessenger = new ParticleMessenger(this);
}

PrimaryGeneratorAction::~PrimaryGeneratorAction()
{
	delete particleGun;
	delete particleMessenger;
}

void PrimaryGeneratorAction::InputCRY()
{
	inputState = 1;
}

void PrimaryGeneratorAction::UpdateCRY(std::string* input)
{
	CRYSetup *setup = new CRYSetup(*input,"../data");

	generator = new CRYGenerator(setup);

	// set randim number generator
	RNGWrapper<CLHEP::HepRandomEngine>::set(CLHEP::HepRandom::getTheEngine(),&CLHEP::HepRandomEngine::flat);
	setup->setRandomFunction(RNGWrapper<CLHEP::HepRandomEngine>::rng);
	inputState=0;
}

void PrimaryGeneratorAction::CRYFromFile(G4String newFilename)
{
	// Read the cry input file
	std::ifstream file;
	file.open(newFilename,std::ios::in);
	char buffer[1000];

	if (file.fail()) {
		G4cout << "Failed to open input file " << newFilename << G4endl;
		G4cout << "Make sure to define the cry library on the command line" << G4endl;
		inputState=-1;
	} else {
	
	std::string setupString("");
	while ( !file.getline(buffer,1000).eof()) {
		setupString.append(buffer);
		setupString.append(" ");
	}

	CRYSetup *setup=new CRYSetup(setupString,"../data");

	generator = new CRYGenerator(setup);

	// set random number generator
	RNGWrapper<CLHEP::HepRandomEngine>::set(CLHEP::HepRandom::getTheEngine(),&CLHEP::HepRandomEngine::flat);
	setup->setRandomFunction(RNGWrapper<CLHEP::HepRandomEngine>::rng);
	inputState=0;
	}
}


void PrimaryGeneratorAction::GeneratePrimaries(G4Event *anEvent)
{
	if (inputState != 0) {
		G4String* str = new G4String("CRY was not successfully initialized");
		G4Exception("PrimaryGeneratorAction","1",RunMustBeAborted,*str);
	}
	G4String particleName;
	vect->clear();
	generator->genEvent(vect);
	// G4cout << "Total time simulated: " << generator->timeSimulated() << " seconds\n";


	//....debug output
	//....debug output
  	// G4cout << "\nEvent=" << anEvent->GetEventID() << " "
    //      << "CRY generated nparticles=" << vect->size()
    //      << G4endl;

	for ( unsigned j=0; j<vect->size(); j++) {
    particleName=CRYUtils::partName((*vect)[j]->id());

    //....debug output  
    // G4cout << "  "          << particleName << " "
    //      << "charge="      << (*vect)[j]->charge() << " "
    //      << "energy (MeV)=" << (*vect)[j]->ke()*MeV << " "
    //      << "pos (m)"
    //      << G4ThreeVector((*vect)[j]->x(), (*vect)[j]->y(), (*vect)[j]->z())
    //      << " " << "direction cosines "
    //      << G4ThreeVector((*vect)[j]->u(), (*vect)[j]->v(), (*vect)[j]->w())
    //      << " " << G4endl;

    // particleGun->SetParticleDefinition(particleTable->FindParticle((*vect)[j]->PDGid()));
    // particleGun->SetParticleEnergy((*vect)[j]->ke()*MeV);
    // particleGun->SetParticleEnergy(4.*GeV);
    // particleGun->SetParticlePosition(G4ThreeVector((*vect)[j]->x()*m, (*vect)[j]->z()*m + 60.0*cm, -(*vect)[j]->y()*m));
	// particleGun->SetParticlePosition(G4ThreeVector(0.*m, 10. *cm, -10. *cm));
    // particleGun->SetParticleMomentumDirection(G4ThreeVector((*vect)[j]->u(), (*vect)[j]->w(), -(*vect)[j]->v()));
    // particleGun->SetParticleMomentumDirection(G4ThreeVector(0, -1, 0));
    particleGun->SetParticleTime((*vect)[j]->t());
    particleGun->GeneratePrimaryVertex(anEvent);
    delete (*vect)[j];
  }
}

#endif
