//For the EA operation Metatrader\EXPERTS\indicators folder must
//contain indicators 5c_OsMA.mq4 and J2JMA.mq4
//+==================================================================+
//|                                                       Exp_11.mq4 |
//|                             Copyright © 2008,   Nikolay Kositsin | 
//|                              Khabarovsk,   farria@mail.redcom.ru | 
//+==================================================================+
#property copyright "Copyright © 2008, Nikolay Kositsin"
#property link "farria@mail.redcom.ru"
//----+ +--------------------------------------------------------------------------+
//---- EA INPUT PARAMETERS FOR BUY TRADES 
extern bool   Test_Up = true;//filter of trade calculations direction
extern double Money_Management_Up = 0.1;
//---- input parameters of the custom indicator J2JMA.mq4
extern int    TimeframeX_Up = 240;
extern int    Length1X_Up = 4;  // depth of the first smoothing
extern int    Phase1X_Up = 100; // parameter of the first smoothing
       //changing in the range -100 ... +100, influences the quality 
       //of the transient process of averaging;  
extern int    Length2X_Up = 4;  // depth of the second smoothing 
extern int    Phase2X_Up = 100; // parameter of the second smoothing, 
       //changing in the range -100 ... +100, influences the quality 
       //of the transient process of averaging;  
extern int    IPCX_Up = 0;/* Selecting prices on which the indicator will 
be calculated (0-CLOSE, 1-OPEN, 2-HIGH, 3-LOW, 4-MEDIAN, 5-TYPICAL, 
6-WEIGHTED, 7-Heiken Ashi Close, 8-SIMPL, 9-TRENDFOLLOW, 10-0.5*TRENDFOLLOW, 
11-Heiken Ashi Low, 12-Heiken Ashi High, 13-Heiken Ashi Open, 
14-Heiken Ashi Close.) */
//---- input parameters of the custom indicator 5c_OsMA.mq4
extern int    Timeframe_Up = 60;
extern double IndLevel_Up = 0; // breakout level of the indicator
extern int    FastEMA_Up = 12;  // quick EMA period
extern int    SlowEMA_Up = 26;  // slow EMA period
extern int    SignalSMA_Up = 9;  // signal SMA period
extern int    STOPLOSS_Up = 50;  // stop loss
extern int    TAKEPROFIT_Up = 100; // take profit
extern int    TRAILINGSTOP_Up = 0; // trailing stop
extern int    PriceLevel_Up =40; // difference between the current price and
                                         // the price of a pending order triggering
extern bool   ClosePos_Up = true; // forced position closing allowed
//----+ +--------------------------------------------------------------------------+
//---- EA INPUT PARAMETERS FOR SELL TRADES
extern bool   Test_Dn = true;//filter of trade calculations direction
extern double Money_Management_Dn = 0.1;
//---- input parameters of the custom indicator J2JMA.mq4
extern int    TimeframeX_Dn = 240;
extern int    Length1X_Dn = 4;  // smoothing depth 
extern int    Phase1X_Dn = 100;  // parameter of the first smoothing 
       //changing in the range -100 ... +100, influences the quality 
       //of the transient process of averaging;  
extern int    Length2X_Dn = 4;  // smoothing depth 
extern int    Phase2X_Dn = 100; // parameter of the second smoothing 
       //changing in the range -100 ... +100, influences the quality 
       //of the transient process of averaging;  
extern int    IPCX_Dn = 0;/* Selecting prices on which the indicator will 
be calculated (0-CLOSE, 1-OPEN, 2-HIGH, 3-LOW, 4-MEDIAN, 5-TYPICAL, 
6-WEIGHTED, 7-Heiken Ashi Close, 8-SIMPL, 9-TRENDFOLLOW, 10-0.5*TRENDFOLLOW, 
11-Heiken Ashi Low, 12-Heiken Ashi High, 13-Heiken Ashi Open, 
14-Heiken Ashi Close.) */
//---- input parameters of the custom indicator 5c_OsMA.mq4
extern int    Timeframe_Dn = 60;
extern double IndLevel_Dn = 0; // breakout level of the indicator
extern int    FastEMA_Dn = 12;  // quick EMA period
extern int    SlowEMA_Dn = 26;  // slow EMA period
extern int    SignalSMA_Dn = 9;  // signal SMA period
extern int    STOPLOSS_Dn = 50;  // stop loss
extern int    TAKEPROFIT_Dn = 100; // take profit
extern int    TRAILINGSTOP_Dn = 0; // trailing stop
extern int    PriceLevel_Dn = 40; // difference between the current price and 
                                         // the price of a pending order triggering
extern bool   ClosePos_Dn = true; // forced position closing allowed
//----+ +--------------------------------------------------------------------------+
//---- Integer variables for the minimum of calculation bars
int MinBarX_Up, MinBar_Up, MinBarX_Dn, MinBar_Dn;
//+==================================================================+
//| TimeframeCheck() functions                                       |
//+==================================================================+
void TimeframeCheck(string Name, int Timeframe)
  {
//----+
   //---- Checking the correctness of Timeframe variable value
   if (Timeframe != 1)
    if (Timeframe != 5)
     if (Timeframe != 15)
      if (Timeframe != 30)
       if (Timeframe != 60)
        if (Timeframe != 240)
         if (Timeframe != 1440)
           Print(StringConcatenate("TimeframeCheck: Parameter ",Name,
                     " cannot ", "be equal to ", Timeframe, "!!!"));    
//----+ 
  }
//+==================================================================+
//| Custom Expert functions                                          |
//+==================================================================+
#include <Lite_EXPERT1.mqh>
//+==================================================================+
//| Custom Expert initialization function                            |
//+==================================================================+
int init()
  {
//---- Checking the correctness of Timeframe_Up variable value
   TimeframeCheck("Timeframe_Up", Timeframe_Up); 
   //---- Checking the correctness of TimeframeX_Up variable value
   TimeframeCheck("TimeframeX_Up", TimeframeX_Up);                                                                        
//---- Checking the correctness of Timeframe_Dn variable value 
   TimeframeCheck("Timeframe_Dn", Timeframe_Dn);
   //---- Checking the correctness of Timeframe_Dn variable value 
   TimeframeCheck("TimeframeX_Dn", TimeframeX_Dn);    
//---- Initialization of variables
   MinBar_Up  = 3 + MathMax(FastEMA_Up, SlowEMA_Up) + SignalSMA_Up;
   MinBarX_Up  = 3 + 30 + 30;
   MinBar_Dn  = 3 + MathMax(FastEMA_Dn, SlowEMA_Dn) + SignalSMA_Dn;
   MinBarX_Dn  = 3 + 30 + 30;                              
//---- end of initialization
   return(0);
  }
//+==================================================================+
//| expert deinitialization function                                 |
//+==================================================================+  
int deinit()
  {
//----+
   
    //---- End of the EA deinitialization
    return(0);
//----+ 
  }
//+==================================================================+
//| Custom Expert iteration function                                 |
//+==================================================================+
int start()
  {
   //----+ Declaring local variables
   double J2JMA1, J2JMA2, Osc1, Osc2;
   //----+ Declaring static variables
   //----+ +---------------------------------------------------------------+
   static double TrendX_Up, TrendX_Dn;
   static datetime StopTime_Up, StopTime_Dn; 
   static int LastBars_Up, LastBarsX_Up, LastBarsX_Dn, LastBars_Dn;
   static bool BUY_Sign, BUY_Stop, SELL_Sign, SELL_Stop;
   //----+ +---------------------------------------------------------------+
   //----++ CODE FOR LONG POSITIONS                                        |
   //----+ +---------------------------------------------------------------+
   if (Test_Up) 
    {
      int IBARS_Up = iBars(NULL, Timeframe_Up);
      int IBARSX_Up = iBars(NULL, TimeframeX_Up);
      
      if (IBARS_Up >= MinBar_Up && IBARSX_Up >= MinBarX_Up)
       {
         //----+ +----------------------+
         //----+ DEFINING TREND         |
         //----+ +----------------------+
         if (LastBarsX_Up != IBARSX_Up)
          {
           //----+ Initialization of variables 
           LastBarsX_Up = IBARSX_Up;
           BUY_Stop = false;
           
           //----+ calculating indicator values for J2JMA   
           J2JMA1 = iCustom(NULL, TimeframeX_Up, 
                                "J2JMA", Length1X_Up, Length2X_Up,
                                             Phase1X_Up, Phase2X_Up,  
                                                     0, IPCX_Up, 0, 1);
           //---                     
           J2JMA2 = iCustom(NULL, TimeframeX_Up, 
                                "J2JMA", Length1X_Up, Length2X_Up,
                                             Phase1X_Up, Phase2X_Up,  
                                                     0, IPCX_Up, 0, 2);
           
           //----+ defining trend
           TrendX_Up = J2JMA1 - J2JMA2;
           //----+ defining a signal for closing trades
           if (TrendX_Up < 0)
                      BUY_Stop = true;                                      
          }
          
         //----+ +----------------------------------------+
         //----+ DEFINING SIGNAL FOR MARKET ENTERING      |
         //----+ +----------------------------------------+
         if (LastBars_Up != IBARS_Up)
          {
           //----+ Initialization of variables 
           BUY_Sign = false;
           LastBars_Up = IBARS_Up;
           StopTime_Up = iTime(NULL, Timeframe_Up, 0)
                                          + 60 * Timeframe_Up;
           //----+ calculating indicator values
           Osc1 = iCustom(NULL, Timeframe_Up, 
                         "5c_OsMA", FastEMA_Up, SlowEMA_Up,
                                               SignalSMA_Up, 5, 1);
           //---                   
           Osc2 = iCustom(NULL, Timeframe_Up, 
                         "5c_OsMA", FastEMA_Up, SlowEMA_Up,
                                               SignalSMA_Up, 5, 2);
           
           //----+ defining signals for trades
           if (TrendX_Up > 0)                                           
            if (Osc2 < IndLevel_Up)
             if (Osc1 > IndLevel_Up)
                        BUY_Sign = true;                               
          }
          
         //----+ +-------------------+
         //----+ EXECUTION OF TRADES |
         //----+ +-------------------+
         if (!OpenBuyLimitOrder1(BUY_Sign, 1, 
              Money_Management_Up, STOPLOSS_Up, TAKEPROFIT_Up,
                                            PriceLevel_Up, StopTime_Up))
                                                                 return(-1);
         if (ClosePos_Up)
                if (!CloseOrder1(BUY_Stop, 1))
                                        return(-1);
                                        
         if (!Make_TreilingStop(1, TRAILINGSTOP_Up))
                                              return(-1);
        }
     }
   //----+ +---------------------------------------------------------------+
   //----++ CODE FOR SHORT POSITIONS                                       |
   //----+ +---------------------------------------------------------------+
   if (Test_Dn) 
    {
      int IBARS_Dn = iBars(NULL, Timeframe_Dn);
      int IBARSX_Dn = iBars(NULL, TimeframeX_Dn);
      
      if (IBARS_Dn >= MinBar_Dn && IBARSX_Dn >= MinBarX_Dn)
       {
         //----+ +----------------------+
         //----+ DEFINING TREND         |
         //----+ +----------------------+
         if (LastBarsX_Dn != IBARSX_Dn)
          {
           //--- Initialization of variables 
           LastBarsX_Dn = IBARSX_Dn;
           SELL_Stop = false;
           
           //----+ calculating indicator values for J2JMA   
           J2JMA1 = iCustom(NULL, TimeframeX_Dn, 
                                "J2JMA", Length1X_Dn, Length2X_Dn,
                                             Phase1X_Dn, Phase2X_Dn,  
                                                     0, IPCX_Dn, 0, 1);
           //---                     
           J2JMA2 = iCustom(NULL, TimeframeX_Dn, 
                                "J2JMA", Length1X_Dn, Length2X_Dn,
                                             Phase1X_Dn, Phase2X_Dn,  
                                                     0, IPCX_Dn, 0, 2);
           
           //----+ defining trend                                 
           TrendX_Dn = J2JMA1 - J2JMA2;
           //----+ defining a signal for closing trades
           if (TrendX_Dn > 0)
                      SELL_Stop = true;                                      
          }
         
         //----+ +----------------------------------------+
         //----+ DEFINING SIGNAL FOR MARKET ENTERING      |
         //----+ +----------------------------------------+
         if (LastBars_Dn != IBARS_Dn)
          {
           //----+ Initialization of variables 
           SELL_Sign = false;
           LastBars_Dn = IBARS_Dn;
           StopTime_Dn = iTime(NULL, Timeframe_Dn, 0)
                                          + 60 * Timeframe_Dn;
           //----+ calculating indicator values    
           Osc1 = iCustom(NULL, Timeframe_Dn, 
                         "5c_OsMA", FastEMA_Dn, SlowEMA_Dn,
                                               SignalSMA_Dn, 5, 1);
           //---                   
           Osc2 = iCustom(NULL, Timeframe_Dn, 
                         "5c_OsMA", FastEMA_Dn, SlowEMA_Dn,
                                               SignalSMA_Dn, 5, 2);
           
           //----+ defining signals for trades
           if (TrendX_Dn < 0)                                           
            if (Osc2 > IndLevel_Dn)
             if (Osc1 < IndLevel_Dn)
                        SELL_Sign = true;                               
          }
          
         //----+ +-------------------+
         //----+ EXECUTION OF TRADES |
         //----+ +-------------------+
          if (!OpenSellLimitOrder1(SELL_Sign, 2, 
              Money_Management_Dn, STOPLOSS_Dn, TAKEPROFIT_Dn,
                                            PriceLevel_Dn, StopTime_Dn))
                                                                 return(-1);
          if (ClosePos_Dn)
                if (!CloseOrder1(SELL_Stop, 2))
                                        return(-1);
                                        
          if (!Make_TreilingStop(2, TRAILINGSTOP_Dn))
                                                  return(-1);
        }
     }
   //----+ +---------------------------------------------------------------+
//----+ 
    
    return(0);
  }