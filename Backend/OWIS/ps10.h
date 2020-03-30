/*
*
* ps10.h
* created:      07.04.2008  alex
* last change:  31.01.2014  alex
*
*/

#ifndef __MYPS10	// Schutz vor Mehrfacheinbindung
#define __MYPS10


#ifdef __cplusplus
extern "C" {
#endif


// System                                                                                 
long    __stdcall PS10_Connect (long,long,long,long,long,long,long,long);              
long    __stdcall PS10_SimpleConnect (long, const char*);                       
long    __stdcall PS10_Disconnect (long);
long    __stdcall PS10_SetCanOpenSlave (long,long);  
long    __stdcall PS10_GetCanOpenSlave (long);  
long    __stdcall PS10_GetSlaves (long);  
long    __stdcall PS10_GetConnectInfo (long,char*,long);                       
long    __stdcall PS10_GetMessage (long,char*,long);                       
long    __stdcall PS10_GetTerminal (long);                        
long    __stdcall PS10_SetTerminal (long,long);  
long    __stdcall PS10_GetBoardVersion (long,char*,long);                       
long    __stdcall PS10_GetSerNumber (long,char*,long);                        
long    __stdcall PS10_GetError (long);                        
long    __stdcall PS10_CheckMem (long);                        
long    __stdcall PS10_ResetBoard (long);                        
long    __stdcall PS10_ClearError (long);                        
                      
// Operate                      
long    __stdcall PS10_MotorInit (long,long);
long    __stdcall PS10_MotorOn (long,long);
long    __stdcall PS10_MotorOff (long,long);                             
long    __stdcall PS10_GetTargetMode (long,long);                     
long    __stdcall PS10_SetTargetMode (long,long,long);                     
long    __stdcall PS10_GetPosition (long,long);
long    __stdcall PS10_SetPosition (long,long,long);
long    __stdcall PS10_ResetCounter (long,long);                                        
long    __stdcall PS10_GetTarget (long,long);                   
long    __stdcall PS10_SetTarget (long,long,long);                   
long    __stdcall PS10_GoTarget (long,long);                                         
long    __stdcall PS10_GoRef (long,long,long);                                  
long    __stdcall PS10_FreeSwitch (long,long);
long    __stdcall PS10_Stop (long,long);                                          
long    __stdcall PS10_GoVel (long,long);                                         
long    __stdcall PS10_StopVel (long,long);                                          
long    __stdcall PS10_GetMotorType (long,long);
long    __stdcall PS10_SetMotorType (long,long,long);                   
long    __stdcall PS10_GetEncLines (long,long);                    
long    __stdcall PS10_SetEncLines (long,long,long);                    
long    __stdcall PS10_GetAxisMonitor (long,long);                    
long    __stdcall PS10_SetAxisMonitor (long,long,long);                    
long    __stdcall PS10_GetAxisState (long,long);                       
long    __stdcall PS10_GetMoveState (long,long);                       
long    __stdcall PS10_GetVelState (long,long);                       
long    __stdcall PS10_GetErrorState (long,long);                       
long    __stdcall PS10_GetRefReady (long,long);
long    __stdcall PS10_GetActF (long,long);                    
long    __stdcall PS10_GetEncPos (long,long);
long    __stdcall PS10_GetPosError (long,long);
long    __stdcall PS10_GetMaxPosError (long,long);
long    __stdcall PS10_SetMaxPosError (long,long,long);
long    __stdcall PS10_GetPosRange (long,long);
                     
// Adjustments
long    __stdcall PS10_SaveAxisParams (long);                    
long    __stdcall PS10_GetAccel (long,long);                    
long    __stdcall PS10_SetAccel (long,long,long); 
long    __stdcall PS10_GetRefDecel (long,long);                    
long    __stdcall PS10_SetRefDecel (long,long,long); 
long    __stdcall PS10_GetPosF (long,long);                    
long    __stdcall PS10_SetPosF (long,long,long);                    
long    __stdcall PS10_GetF (long,long);                    
long    __stdcall PS10_SetF (long,long,long);                    
long    __stdcall PS10_GetSlowRefF (long,long);                    
long    __stdcall PS10_SetSlowRefF (long,long,long);                    
long    __stdcall PS10_GetFastRefF (long,long);                    
long    __stdcall PS10_SetFastRefF (long,long,long);                    
long    __stdcall PS10_GetFreeF (long,long);                    
long    __stdcall PS10_SetFreeF (long,long,long);                    
long    __stdcall PS10_GetStepWidth (long,long);                    
long    __stdcall PS10_SetStepWidth (long,long,long);                    
long    __stdcall PS10_GetDriveCurrent (long,long);                    
long    __stdcall PS10_SetDriveCurrent (long,long,long);                    
long    __stdcall PS10_GetHoldCurrent (long,long);                    
long    __stdcall PS10_SetHoldCurrent (long,long,long);                    
long    __stdcall PS10_GetPhaseInitTime (long,long);                    
long    __stdcall PS10_SetPhaseInitTime (long,long,long);                    
long    __stdcall PS10_GetPhasePwmFreq (long,long);                    
long    __stdcall PS10_SetPhasePwmFreq (long,long,long);                    
long    __stdcall PS10_GetCurrentLevel (long,long);                    
long    __stdcall PS10_SetCurrentLevel (long,long,long);                    
long    __stdcall PS10_GetServoLoopMax (long,long);                    
long    __stdcall PS10_SetServoLoopMax (long,long,long);                    

// Software/hardware regulator
long    __stdcall PS10_GetSampleTime (long,long);                    
long    __stdcall PS10_SetSampleTime (long,long,long);                    
long    __stdcall PS10_GetKP (long,long);                    
long    __stdcall PS10_SetKP (long,long,long);                    
long    __stdcall PS10_GetKI (long,long);                    
long    __stdcall PS10_SetKI (long,long,long);                    
long    __stdcall PS10_GetKD (long,long);                    
long    __stdcall PS10_SetKD (long,long,long);                    
long    __stdcall PS10_GetDTime (long,long);                    
long    __stdcall PS10_SetDTime (long,long,long);                    
long    __stdcall PS10_GetILimit (long,long);                    
long    __stdcall PS10_SetILimit (long,long,long);                    

// Switches
long    __stdcall PS10_GetLimitSwitch (long,long);                                   
long    __stdcall PS10_SetLimitSwitch (long,long,long);                                   
long    __stdcall PS10_GetLimitSwitchMode (long,long);                                   
long    __stdcall PS10_SetLimitSwitchMode (long,long,long); 
long    __stdcall PS10_GetRefSwitch (long,long);                    
long    __stdcall PS10_SetRefSwitch (long,long,long);                    
long    __stdcall PS10_GetRefSwitchMode (long,long);                    
long    __stdcall PS10_SetRefSwitchMode (long,long,long);                    
long    __stdcall PS10_GetSwitchState (long,long);                                   
long    __stdcall PS10_GetSwitchHyst (long,long);                                   
long    __stdcall PS10_GetLimitControl (long,long);                                   
long    __stdcall PS10_SetLimitControl (long,long,long);                                   
long    __stdcall PS10_GetLimitMin (long,long);                                   
long    __stdcall PS10_SetLimitMin (long,long,long);                                   
long    __stdcall PS10_GetLimitMax (long,long);                                   
long    __stdcall PS10_SetLimitMax (long,long,long);                                   
long    __stdcall PS10_GetLimitState (long,long);                                   
 
// Joystick 
long    __stdcall PS10_JoystickOn (long);                          
long    __stdcall PS10_JoystickOff (long);
long    __stdcall PS10_GetJoyF (long,long);                                   
long    __stdcall PS10_SetJoyF (long,long,long);          
long    __stdcall PS10_GetJoyZone (long);                                   
long    __stdcall PS10_SetJoyZone (long,long);          
long    __stdcall PS10_GetJoyZero (long);                                   
long    __stdcall PS10_SetJoyZero (long,long);          
long    __stdcall PS10_GetJoyButton (long);                                   
long    __stdcall PS10_SetJoyButton (long,long);          

// Analog & digital I/O  
long    __stdcall PS10_GetDigitalInput (long,long);                                   
long    __stdcall PS10_GetDigitalOutput (long,long);                                   
long    __stdcall PS10_SetDigitalOutput (long,long,long);                                   
long    __stdcall PS10_GetAnalogInput (long,long);                                   
long    __stdcall PS10_GetPwmOutput (long,long);                                   
long    __stdcall PS10_SetPwmOutput (long,long,long);                                   
long    __stdcall PS10_GetOutputMode (long);                                   
long    __stdcall PS10_SetOutputMode (long,long);                                   
long    __stdcall PS10_GetPwmBrake (long,long);                                   
long    __stdcall PS10_SetPwmBrake (long,long,long);                                   
long    __stdcall PS10_GetPwmBrakeValue1 (long,long);                                   
long    __stdcall PS10_SetPwmBrakeValue1 (long,long,long);                                   
long    __stdcall PS10_GetPwmBrakeValue2 (long,long);                                   
long    __stdcall PS10_SetPwmBrakeValue2 (long,long,long);                                   
long    __stdcall PS10_GetPwmBrakeTime (long,long);                                   
long    __stdcall PS10_SetPwmBrakeTime (long,long,long);                                   
long    __stdcall PS10_GetPowerMode (long,long);                                   
long    __stdcall PS10_SetPowerMode (long,long,long);                                   
long    __stdcall PS10_GetPowerState (long,long);                                   
long    __stdcall PS10_GetEmergencyInput (long);                                   
                                      
// Extended functions                                       
long    __stdcall PS10_SetStageAttributes (long,long,double,long,double);          
long    __stdcall PS10_SetCalcResol (long,long,double);          
double  __stdcall PS10_GetPositionEx (long,long);                   
long    __stdcall PS10_SetPositionEx (long,long,double);
double  __stdcall PS10_GetTargetEx (long,long);                   
long    __stdcall PS10_SetTargetEx (long,long,double);
double  __stdcall PS10_GetPosRangeEx (long,long);                   
double  __stdcall PS10_GetEncPosEx (long,long);                   
double  __stdcall PS10_GetLimitMinEx (long,long);                   
long    __stdcall PS10_SetLimitMinEx (long,long,double);
double  __stdcall PS10_GetLimitMaxEx (long,long);                   
long    __stdcall PS10_SetLimitMaxEx (long,long,double);
long    __stdcall PS10_MoveEx (long,long,double,long);                              
double  __stdcall PS10_GetPosFEx (long,long);                    
long    __stdcall PS10_SetPosFEx (long,long,double);                    
double  __stdcall PS10_GetFEx (long,long);                    
long    __stdcall PS10_SetFEx (long,long,double);                    
double  __stdcall PS10_GetSlowRefFEx (long,long);                    
long    __stdcall PS10_SetSlowRefFEx (long,long,double);                    
double  __stdcall PS10_GetFastRefFEx (long,long);                    
long    __stdcall PS10_SetFastRefFEx (long,long,double);                    
double  __stdcall PS10_GetFreeFEx (long,long);                    
long    __stdcall PS10_SetFreeFEx (long,long,double);                    
double  __stdcall PS10_GetJoyFEx (long,long);                                   
long    __stdcall PS10_SetJoyFEx (long,long,double);          
double  __stdcall PS10_GetActFEx (long,long);                    
double  __stdcall PS10_GetAccelEx (long,long);                    
long    __stdcall PS10_SetAccelEx (long,long,double); 
double  __stdcall PS10_GetRefDecelEx (long,long);                    
long    __stdcall PS10_SetRefDecelEx (long,long,double); 
long    __stdcall PS10_SetDEC (long, long, const char*, const char*, long, double);                       
long    __stdcall PS10_GetDEC (long, long, char*, long);                       

// Communication                                        
long    __stdcall PS10_LogFile (long, long, const char*, long, long);                    
long	__stdcall PS10_CmdAns (long, const char*, char*, long, long);
long	__stdcall PS10_CmdAnsEx (long, const char*, char*, long, long, long);
long	__stdcall PS10_GetOWISidData (long, long, long, char*, long);
long    __stdcall PS10_GetReadError (long); 
                    
#ifdef __cplusplus
};
#endif

#endif	//__MYPS10
