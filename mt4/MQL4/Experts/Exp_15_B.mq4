//+==================================================================+
//|                                                     Exp_15_B.mq4 |
//|                             Copyright � 2008,   Nikolay Kositsin | 
//|                              Khabarovsk,   farria@mail.redcom.ru | 
//+==================================================================+
#property copyright "Copyright � 2008, Nikolay Kositsin"
#property link "farria@mail.redcom.ru"
//----+ +---------------------------------------------------------------------------+
//---- ������� ��������� �������� ��� BUY ������ 
extern bool   Test_Up = true;//������ ����������� �������� ������
extern double Money_Management_Up = 0.1;
//---- + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +   
extern int    TimeframeX_Up = 1440;                 
extern int    PeriodWATR_Up = 10; 
extern double Kwatr_Up = 1.0000; 
extern int    HighLow_Up = 0; 
//---- + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
extern int    Timeframe_Up = 240;
extern int    JJLength_Up = 8;  // ������� JJMA ����������� ������� ����
extern int    JXLength_Up = 8;  // ������� JurX ����������� ����������� ���������� 
extern int    Phase_Up = 100;// ��������, ������������ � ��������
                        // -100 ... +100, ������ �� �������� ����������� ��������; 
extern int    IPC_Up = 0; /* ����� ���, �� ������� ������������ ������ 
���������� (0-CLOSE, 1-OPEN, 2-HIGH, 3-LOW, 4-MEDIAN, 5-TYPICAL, 
6-WEIGHTED, 7-Heiken Ashi Close, 8-SIMPL, 9-TRENDFOLLOW, 10-0.5*TRENDFOLLOW, 
11-Heiken Ashi Low, 12-Heiken Ashi High, 13-Heiken Ashi Open, 
14-Heiken Ashi Close.) */
//---- + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
extern int    TimeframeN_Up = 15;
// ���������� � ������������� ������� ���������� �������� ��� ������ ��� �������� ����������
//---- + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
extern int    STOPLOSS_Up = 50;  // ��������
extern int    TAKEPROFIT_Up = 100; // ����������
extern bool   ClosePos_Up = true; // ���������� ��������������� ���������� �������
//----+ +---------------------------------------------------------------------------+
//---- ������� ��������� �������� ��� SELL ������ 
extern bool   Test_Dn = true;//������ ����������� �������� ������
extern double Money_Management_Dn = 0.1;
//---- + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
extern int    TimeframeX_Dn = 1440;
extern int    PeriodWATR_Dn = 10; 
extern double Kwatr_Dn = 1.0000; 
extern int    HighLow_Dn = 0; 
//---- + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
extern int    Timeframe_Dn = 240;
extern int    JJLength_Dn = 8;  // ������� JJMA ����������� ������� ����
extern int    JXLength_Dn = 8;  // ������� JurX ����������� ����������� ���������� 
extern int    Phase_Dn = 100;// ��������, ������������ � ��������
                        // -100 ... +100, ������ �� �������� ����������� ��������; 
extern int    IPC_Dn = 0; /* ����� ���, �� ������� ������������ ������ 
���������� (0-CLOSE, 1-OPEN, 2-HIGH, 3-LOW, 4-MEDIAN, 5-TYPICAL, 
6-WEIGHTED, 7-Heiken Ashi Close, 8-SIMPL, 9-TRENDFOLLOW, 10-0.5*TRENDFOLLOW, 
11-Heiken Ashi Low, 12-Heiken Ashi High, 13-Heiken Ashi Open, 
14-Heiken Ashi Close.) */
//---- + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
extern int    TimeframeN_Dn = 15;
// ���������� � ������������� ������� ���������� �������� ��� ������ ��� �������� ����������
//---- + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
extern int    STOPLOSS_Dn = 50;  // ��������
extern int    TAKEPROFIT_Dn = 100; // ����������
extern bool   ClosePos_Dn = true; // ���������� ��������������� ���������� �������
//----+ +---------------------------------------------------------------------------+
//---- ����� ���������� ��� �������� ��������� �����
int MinBar_Up, MinBar_Dn, MinBarX_Up, MinBarX_Dn, MinBarN_Up, MinBarN_Dn;
//+==================================================================+
//| Custom Expert functions                                          |
//+==================================================================+
#include <Lite_EXPERT1.mqh>
//+==================================================================+
//| TimeframeCheck() functions                                       |
//+==================================================================+
void TimeframeCheck(string Name, int Timeframe)
  {
//----+
   //---- �������� �������� ���������� Timeframe �� ������������
   if (Timeframe != 1)
    if (Timeframe != 5)
     if (Timeframe != 15)
      if (Timeframe != 30)
       if (Timeframe != 60)
        if (Timeframe != 240)
         if (Timeframe != 1440)
           Print(StringConcatenate("�������� ",Name,
                     " �� ����� ", "���� ������ ", Timeframe, "!!!"));    
//----+ 
  }
//+==================================================================+
//| Custom Expert initialization function                            |
//+==================================================================+
int init()
  {
//---- �������� �������� ���������� ����������� �� ������������
   TimeframeCheck("TimeframeX_Up", TimeframeX_Up);
   TimeframeCheck("Timeframe_Up", Timeframe_Up);
   TimeframeCheck("TimeframeN_Up", TimeframeN_Up);

//---- �������� �������� ���������� ����������� �� ������������ 
   TimeframeCheck("TimeframeX_Dn", TimeframeX_Dn); 
   TimeframeCheck("Timeframe_Dn", Timeframe_Dn); 
   TimeframeCheck("TimeframeN_Dn", TimeframeN_Dn);

//---- ������������� ����������             
   MinBarX_Up = 2 + PeriodWATR_Up;
   MinBar_Up = 4 + 3 * JXLength_Up + 30;
   MinBarN_Up = 0;

//---- ������������� ���������� 
   MinBarX_Dn = 2 + PeriodWATR_Dn;
   MinBar_Dn = 4 + 3 * JXLength_Dn + 30;
   MinBarN_Dn = 0;
                                          
//---- ���������� �������������
   return(0);
  }
//+==================================================================+
//| expert deinitialization function                                 |
//+==================================================================+  
int deinit()
  {
//----+
   
    //---- ���������� ��������������� ��������
    return(0);
//----+ 
  }
//+==================================================================+
//| Custom Expert iteration function                                 |
//+==================================================================+
int start()
  {
   //----+ ���������� ��������� ���������� ���������� ������
   int    bar;
   double JCCIX[2], Trend, Fast_StepMA, Slow_StepMA;
   
   //----+ ���������� ����������� ���������� ���������� ������
   static double   OldTrend_Up, OldTrend_Dn;
   static bool   SecondStart_Up, SecondStart_Dn;
   
   //----+ ���������� ����������� ����������
   static datetime StopTime_Up, StopTime_Dn;
   //---
   static int  LastBars_Up, LastBars_Dn;
   static int  LastBarsX_Up, LastBarsX_Dn; 
   static int  LastBarsN_Up, LastBarsN_Dn;
   //---
   static bool BUY_Sign, BUY_Stop;
   static bool SELL_Sign, SELL_Stop;
   static bool NoiseBUY_Sign, NoiseSELL_Sign;
   static double TrendX_Up, TrendX_Dn;
      
   //----+ +---------------------------------------------------------------+
   //----++ ��� ��� ������� �������                                        |
   //----+ +---------------------------------------------------------------+
   if (Test_Up) 
    {
      int IBARS_Up = iBars(NULL, Timeframe_Up);
      int IBARSX_Up = iBars(NULL, TimeframeX_Up);
      int IBARSN_Up = iBars(NULL, TimeframeN_Up);
      //---
      if (IBARS_Up >= MinBar_Up && IBARSX_Up >= MinBarX_Up && IBARSN_Up >= MinBarN_Up)
       {       
         //----+ +----------------------+
         //----+ ����������� ������     |
         //----+ +----------------------+
         if (LastBarsX_Up != IBARSX_Up)
          {
           //----+ ������������� ���������� 
           LastBarsX_Up = IBARSX_Up;
           BUY_Sign = false;
           BUY_Stop = false;
           
           //----+ ���������� ������������ ��������
           Fast_StepMA = iCustom(NULL, TimeframeX_Up, "StepMA_Stoch_NK", 
                                 PeriodWATR_Up, Kwatr_Up, HighLow_Up, 0, 1);
           //---         
           Slow_StepMA = iCustom(NULL, TimeframeX_Up, "StepMA_Stoch_NK", 
                                 PeriodWATR_Up, Kwatr_Up, HighLow_Up, 1, 1);
           //----+ ����������� ������                                 
           TrendX_Up = Fast_StepMA - Slow_StepMA;
           //----+ ����������� ������� ��� ���������� ������
           if (TrendX_Up < 0)
                      BUY_Stop = true;                                      
          }
          
         //----+ +----------------------------------------+
         //----+ ����������� �������� ��� ����� � �����   |
         //----+ +----------------------------------------+
         if (LastBars_Up != IBARS_Up && TrendX_Up > 0)
          {
           //----+ ������������� ���������� 
           BUY_Sign = false;
           LastBars_Up = IBARS_Up;
           //----+ ������������� ������� ���������� 
           NoiseBUY_Sign = false;
           StopTime_Up = iTime(NULL, Timeframe_Up, 0)
                                          + 50 * Timeframe_Up;
           
           //----+ ������������� ����
           if (!SecondStart_Up)
            {
              //--- ����� ����������� ������ �� ������ ������
              for(bar = 2; bar < IBARS_Up - 1; bar++)
               {
                 JCCIX[0] = iCustom(NULL, Timeframe_Up, 
                    "JCCIX", JJLength_Up, JXLength_Up, Phase_Up, IPC_Up, 0, bar); 
                 //---  
                 JCCIX[1] =  iCustom(NULL, Timeframe_Up, 
                    "JCCIX", JJLength_Up, JXLength_Up, Phase_Up, IPC_Up, 0, bar + 1); 
                 //---  
                 OldTrend_Up = JCCIX[0] - JCCIX[1];
                 //---    
                 if (OldTrend_Up != 0)
                   {
                    SecondStart_Up = true;
                    break;
                   }
               }
            } 
           
           //----+ ���������� ������������ �������� � �������� �� � �����      
           for(bar = 1; bar < 3; bar++)
                     JCCIX[bar - 1] =                  
                         iCustom(NULL, Timeframe_Up, 
                                "JCCIX", JJLength_Up, JXLength_Up, 
                                                   Phase_Up, IPC_Up, 0, bar);
           
           //----+ ����������� �������� ��� ������   
           Trend = JCCIX[0] - JCCIX[1];
            
           if (TrendX_Up > 0)                     
              if (OldTrend_Up < 0)
                         if (Trend > 0)
                                 BUY_Sign = true; 
           if (Trend != 0)
                   OldTrend_Up = Trend;                                   
          }
         
         //----+ +------------------------------------------------+
         //----+ ����������� ������� �������� ��� ����� � �����   |
         //----+ +------------------------------------------------+
         if (BUY_Sign)
          if (LastBarsN_Up != IBARSN_Up)
           {
             NoiseBUY_Sign = false;
             LastBarsN_Up = IBARSN_Up;
             //---
             
             // �������� ��� ��������� ����� ����� � ����� �� ������� ����������
                                            //(������������� ���������� NoiseBUY_Sign)
             NoiseBUY_Sign = true;                              
           }
         
         //----+ +-------------------+
         //----+ ���������� ������   |
         //----+ +-------------------+
         if (NoiseBUY_Sign)
           if (!OpenBuyOrder1(BUY_Sign, 1, Money_Management_Up, 
                                          STOPLOSS_Up, TAKEPROFIT_Up))
                                                                 return(-1);
         if (ClosePos_Up)
                if (!CloseOrder1(BUY_Stop, 1))
                                        return(-1);
        }
     }
     
   //----+ +---------------------------------------------------------------+
   //----++ ��� ��� �������� �������                                       |
   //----+ +---------------------------------------------------------------+
   if (Test_Dn) 
    {
      int IBARS_Dn = iBars(NULL, Timeframe_Dn);
      int IBARSX_Dn = iBars(NULL, TimeframeX_Dn);
      int IBARSN_Dn = iBars(NULL, TimeframeN_Dn);
      //---
      if (IBARS_Dn >= MinBar_Dn && IBARSX_Dn >= MinBarX_Dn && IBARSN_Dn >= MinBarN_Dn)
       {
         //----+ +----------------------+
         //----+ ����������� ������     |
         //----+ +----------------------+
         if (LastBarsX_Dn != IBARSX_Dn)
          {
           //----+ ������������� ���������� 
           LastBarsX_Dn = IBARSX_Dn;
           SELL_Sign = false;
           SELL_Stop = false;
           
           //----+ ���������� ������������ ��������
           Fast_StepMA = iCustom(NULL, TimeframeX_Dn, "StepMA_Stoch_NK", 
                                 PeriodWATR_Dn, Kwatr_Dn, HighLow_Dn, 0, 1);
           //---         
           Slow_StepMA = iCustom(NULL, TimeframeX_Dn, "StepMA_Stoch_NK", 
                                 PeriodWATR_Dn, Kwatr_Dn, HighLow_Dn, 1, 1);
           //----+ ����������� ������                                 
           TrendX_Dn = Fast_StepMA - Slow_StepMA;
           //----+ ����������� ������� ��� ���������� ������
           if (TrendX_Dn > 0)
                      SELL_Stop = true;                                      
          }
         
         //----+ +----------------------------------------+
         //----+ ����������� �������� ��� ����� � �����   |
         //----+ +----------------------------------------+
         if (LastBars_Dn != IBARS_Dn && TrendX_Dn < 0)
          {
           //----+ ������������� ���������� 
           SELL_Sign = false;
           LastBars_Dn = IBARS_Dn;
           //----+ ������������� ������� ���������� 
           NoiseSELL_Sign = false;
           StopTime_Dn = iTime(NULL, Timeframe_Dn, 0)
                                          + 50 * Timeframe_Dn;
           
           //----+ ������������� ����
           if (!SecondStart_Dn)
            {
              //--- ����� ����������� ������ �� ������ ������
              for(bar = 2; bar < IBARS_Dn - 1; bar++)
               {
                 JCCIX[0] = iCustom(NULL, Timeframe_Dn, 
                    "JCCIX", JJLength_Dn, JXLength_Dn, Phase_Dn, IPC_Dn, 0, bar); 
                 //---  
                 JCCIX[1] =  iCustom(NULL, Timeframe_Dn, 
                    "JCCIX", JJLength_Dn, JXLength_Dn, Phase_Dn, IPC_Dn, 0, bar + 1); 
                 //---  
                 OldTrend_Dn = JCCIX[0] - JCCIX[1];
                 //---    
                 if (OldTrend_Dn != 0)
                   {
                    SecondStart_Dn = true;
                    break;
                   }
               }
            } 
           
           //----+ ���������� ������������ �������� � �������� �� � �����     
           for(bar = 1; bar < 3; bar++)
                     JCCIX[bar - 1]=                  
                         iCustom(NULL, Timeframe_Dn, 
                                "JCCIX", JJLength_Dn, JXLength_Dn, 
                                                   Phase_Dn, IPC_Dn, 0, bar);
           //----+ ����������� �������� ��� ������   
           Trend = JCCIX[0] - JCCIX[1];
           //--- 
           if (TrendX_Dn < 0)                                 
              if (OldTrend_Dn > 0)
                         if (Trend < 0)
                                 SELL_Sign = true;
           if (Trend != 0)
                   OldTrend_Dn = Trend;                                         
          }
         
         //----+ +------------------------------------------------+
         //----+ ����������� ������� �������� ��� ����� � �����   |
         //----+ +------------------------------------------------+
         if (SELL_Sign)
          if (LastBarsN_Dn != IBARSN_Dn)
           {
             NoiseSELL_Sign = false;
             LastBarsN_Dn = IBARSN_Dn;
             //---
             
             // �������� ��� ��������� ����� ����� � ����� �� ������� ����������
                                           //(������������� ���������� NoiseSELL_Sign)
             NoiseSELL_Sign = true;
    
           }
          
          
         //----+ +-------------------+
         //----+ ���������� ������   |
         //----+ +-------------------+
         if (NoiseSELL_Sign)
           if (!OpenSellOrder1(SELL_Sign, 2, Money_Management_Dn, 
                                            STOPLOSS_Dn, TAKEPROFIT_Dn))
                                                                  return(-1);
           if (ClosePos_Dn)
                if (!CloseOrder1(SELL_Stop, 2))
                                        return(-1);
        }
     }
//----+ 
    
    return(0);
  }
//+------------------------------------------------------------------+