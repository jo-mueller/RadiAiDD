// ps10tool.c : Definiert den Einsprungpunkt für die Konsolenanwendung.
//

#include <stdio.h>
#include <stdlib.h>
#include <tchar.h>
#include "ps10.h"


int main(int argc, char* argv[])
{
	// parameters from the command line
	// parameter 1 (COM port)
	long nComPort=5; //argv[1]
	// parameter 2 (axis number)
	long nAxis=1; 
	// parameter 3 (positioning velocity in Hz)
	long nPosF=50000; //argv[2]
	// parameter 4 (distance for positioning in mm, distance=0 - reference run)
	double dDistance=10.0; //argv[3]

	if( argc != 4 ) {
		printf( _T("ps10tool <COM port> <velocity> <distance>\n") );
		printf( _T("e.g. ps10tool 5 50000 10\n") );
		exit(255);
	};

	// set parameters *************
	nComPort=atol(argv[1]);
	nPosF=atol(argv[2]);
	dDistance=atof(argv[3]);
	// ****************************

	// open virtual serial interface
	PS10_Connect(1, 0, nComPort, 9600, 0, 0, 8, 0);	

	// define constants for calculation Inc -> mm
//	PS10_SetStageAttributes(1,nAxis,1.0,200,1.0);

	// initialize axis
	PS10_MotorInit(1,nAxis);

	// set target mode (0 - relative)
	PS10_SetTargetMode(1,nAxis,0);

	// set velocity
	PS10_SetPosF(1,nAxis,nPosF);

	// check position
	printf(_T("Position=%.3f\n"), PS10_GetPositionEx(1,nAxis));

	// start positioning
	if(dDistance==0.0) // go home (to start position)
	{
		PS10_GoRef(1,nAxis,4);
	}
	else // move to target position (+ positive direction, - negative direction)
	{
		PS10_MoveEx(1,nAxis,dDistance,1);
	}

	// check move state of the axis
	printf(_T("Axis is moving...\n"));
	while(PS10_GetMoveState(1,nAxis)) {;}
	printf(_T("Axis is in position.\n"));

	// check position
	printf(_T("Position=%.3f\n"), PS10_GetPositionEx(1,nAxis));

	// close interface
	PS10_Disconnect(1);

	return 0;
}
