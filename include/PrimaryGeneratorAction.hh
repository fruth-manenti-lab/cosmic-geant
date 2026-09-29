#ifndef PrimaryGeneratorAction_HH
#define PrimaryGeneratorAction_HH

#include "G4VUserPrimaryGeneratorAction.hh"

#if defined(ADD_RADIOACTIVE) || defined(ADD_BACKGROUND_GPS)

#include "G4GeneralParticleSource.hh"
#include "G4IonTable.hh"

#elif defined(ADD_SCAN)

#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"

#include <vector>

#else

#include "ParticleMessenger.hh"
#ifdef ADD_CRY_BACKGROUND_GPS
#include "G4GeneralParticleSource.hh"
#endif
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"

#include "vector"
#include "CRYSetup.h"
#include "CRYParticle.h"
#include "CRYGenerator.h"
#include "RNGWrapper.hh"

#endif

#include "G4SystemOfUnits.hh"
#include "G4Event.hh"

// Get instances of some of the useful G4 predefined classes
class G4ParticleGun;                                            // Get it? Because it shoots the particle XDDDDD
class G4Event;                                                  // The event is a collection of shots
#if !defined(ADD_RADIOACTIVE) && !defined(ADD_BACKGROUND_GPS)
class G4ParticleDefinition;                                     // Store parameters of a particle
class ParticleMessenger;                                        // Class that handles user input
#endif 

#ifdef ADD_SCAN
class ScanMessenger;
#endif

class PrimaryGeneratorAction : public G4VUserPrimaryGeneratorAction
{
	public:
		PrimaryGeneratorAction(const char* filename);
		~PrimaryGeneratorAction();
	
		void GeneratePrimaries(G4Event* event);
#ifdef ADD_SCAN
		void SetScanPositionFile(const G4String& path);
#endif
#if !defined(ADD_RADIOACTIVE) && !defined(ADD_BACKGROUND_GPS) && !defined(ADD_SCAN)
		void InputCRY();
		void UpdateCRY(std::string* input);
		void CRYFromFile(G4String newFilename);
		CRYGenerator* generator;
#endif
	private:

#if defined(ADD_RADIOACTIVE) || defined(ADD_BACKGROUND_GPS)
		G4GeneralParticleSource* particleGun;
#elif defined(ADD_SCAN)
		struct ScanPosition {
			G4int index = -1;
			G4ThreeVector position;
		};

		G4ParticleGun* particleGun;
		G4ParticleTable* particleTable;
		std::vector<ScanPosition> scanPositions;
		ScanMessenger* scanMessenger = nullptr;
		G4String scanPositionFile;
		G4bool scanPositionsLoaded = false;

		void LoadScanPositions(const G4String& path);
		G4String ResolveScanPositionFile(const char* filename) const;
#else
		G4ParticleGun* particleGun;
#ifdef ADD_CRY_BACKGROUND_GPS
		G4GeneralParticleSource* backgroundGun;
#endif
		std::vector<CRYParticle*> *vect;
		G4ParticleTable* particleTable;
		G4int inputState;
		ParticleMessenger* particleMessenger;
#endif

};


#endif
