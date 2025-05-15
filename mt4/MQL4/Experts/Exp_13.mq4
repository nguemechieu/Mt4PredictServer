//+==================================================================+
//|                                                       Exp_13.mq4 |
//|                             Copyright � 2007,   Nikolay Kositsin | 
//|                              Khabarovsk,   farria@mail.redcom.ru | 
//+==================================================================+
#property copyright "Copyright � 2007, Nikolay Kositsin"
#property link "farria@mail.redcom.ru"
//----+ +---------------------------------------------------------------------------+
//---- ������� ��������� �������� ��� BUY ������ 
extern bool   Test_Up = true;//������ ����������� �������� ������
extern double Money_Management_Up = 0.1;
//----
extern int    TimeframeX_Up = 1440;
extern double FastLimitX_Up = 0.5;
extern double SlowLimitX_Up = 0.05;
extern int    IPCX_Up = 9;/* ����� ���, �� ������� ������������ ������ ���������� 
(0-CLOSE, 1-OPEN, 2-HIGH, 3-LOW, 4-MEDIAN, 5-TYPICAL, 6-WEIGHTED, 
7-Heiken Ashi Close, 8-SIMPL, 9-TRENDFOLLOW, 10-0.5*TRENDFOLLOW, 
11-Heiken Ashi Low, 12-Heiken Ashi High, 13-Heiken Ashi Open, 
14-Heiken Ashi Close, 15-Heiken Ashi Open0.) */
//---- + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
extern int    Timeframe_Up = 60;
extern int    Length_Up = 4;  // ������� ����������� 
extern int    Phase_Up = 100; // ��������, ������������ � �������� 
          //-100 ... +100, ������ �� �������� ����������� ��������; 
extern int    IPC_Up = 0;/* ����� ���, �� ������� ������������ ������ 
���������� (0-CLOSE, 1-OPEN, 2-HIGH, 3-LOW, 4-MEDIAN, 5-TYPICAL, 
6-WEIGHTED, 7-Heiken Ashi Close, 8-SIMPL, 9-TRENDFOLLOW, 10-0.5*TRENDFOLLOW, 
11-Heiken Ashi Low, 12-Heiken Ashi High, 13-Heiken Ashi Open, 
14-Heiken Ashi Close.) */
//---- + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
extern int    TimeframeY_Up = 5;
extern int    LengthY_Up = 4;  // ������� ����������� 
extern int    PhaseY_Up = 100; // ��������, ������������ � �������� 
          //-100 ... +100, ������ �� �������� ����������� ��������; 
extern int    IPCY_Up = 0;/* ����� ���, �� ������� ������������ ������ 
���������� (0-CLOSE, 1-OPEN, 2-HIGH, 3-LOW, 4-MEDIAN, 5-TYPICAL, 
6-WEIGHTED, 7-Heiken Ashi Close, 8-SIMPL, 9-TRENDFOLLOW, 10-0.5*TRENDFOLLOW, 
11-Heiken Ashi Low, 12-Heiken Ashi High, 13-Heiken Ashi Open, 
14-Heiken Ashi Close.) */
//---- + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
extern int    STOPLOSS_Up = 50;  // ��������
extern int    TAKEPROFIT_Up = 100; // ����������
extern bool   ClosePos_Up = true; // ���������� ��������������� ���������� �������
//----+ +---------------------------------------------------------------------------+
//---- ������� ��������� �������� ��� SELL ������ 
extern bool   Test_Dn = true;//������ ����������� �������� ������
extern double Money_Management_Dn = 0.1;
//----
extern int    TimeframeX_Dn = 1440;
extern double FastLimitX_Dn = 0.5;
extern double SlowLimitX_Dn = 0.05;
extern int    IPCX_Dn = 9;/* ����� ���, �� ������� ������������ ������ ���������� 
(0-CLOSE, 1-OPEN, 2-HIGH, 3-LOW, 4-MEDIAN, 5-TYPICAL, 6-WEIGHTED, 
7-Heiken Ashi Close, 8-SIMPL, 9-TRENDFOLLOW, 10-0.5*TRENDFOLLOW, 
11-Heiken Ashi Low, 12-Heiken Ashi High, 13-Heiken Ashi Open, 
14-Heiken Ashi Close, 15-Heiken Ashi Open0.) */
//---- + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
extern int    Timeframe_Dn = 60;
extern int    Length_Dn = 4;  // ������� ����������� 
extern int    Phase_Dn = 100; // ��������, ������������ � ��������
         // -100 ... +100, ������ �� �������� ����������� ��������; 
extern int    IPC_Dn = 0;/* ����� ���, �� ������� ������������ ������ 
���������� (0-CLOSE, 1-OPEN, 2-HIGH, 3-LOW, 4-MEDIAN, 5-TYPICAL, 
6-WEIGHTED, 7-Heiken Ashi Close, 8-SIMPL, 9-TRENDFOLLOW, 10-0.5*TRENDFOLLOW, 
11-Heiken Ashi Low, 12-Heiken Ashi High, 13-Heiken Ashi Open, 
14-Heiken Ashi Close.) */
//---- + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
extern int    TimeframeY_Dn = 5;
extern int    LengthY_Dn = 4;  // ������� ����������� 
extern int    PhaseY_Dn = 100; // ��������, ������������ � ��������
         // -100 ... +100, ������ �� �������� ����������� ��������; 
extern int    IPCY_Dn = 0;/* ����� ���, �� ������� ������������ ������ 
���������� (0-CLOSE, 1-OPEN, 2-HIGH, 3-LOW, 4-MEDIAN, 5-TYPICAL, 
6-WEIGHTED, 7-Heiken Ashi Close, 8-SIMPL, 9-TRENDFOLLOW, 10-0.5*TRENDFOLLOW, 
11-Heiken Ashi Low, 12-Heiken Ashi High, 13-Heiken Ashi Open, 
14-Heiken Ashi Close.) */
//---- + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
extern int   STOPLOSS_Dn = 50;  // ��������
extern int   TAKEPROFIT_Dn = 100; // ����������
extern bool   ClosePos_Dn = true; // ���������� ��������������� ���������� �������
//----+ +---------------------------------------------------------------------------+
//---- ����� ���������� ��� �������� ��������� �����
int MinBar_Up, MinBar_Dn, MinBarX_Up, MinBarX_Dn, MinBarY_Up, MinBarY_Dn;
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
//---- �������� �������� ���������� Timeframe_Up �� ������������
   TimeframeCheck("TimeframeX_Up", TimeframeX_Up);
//---- �������� �������� ���������� Timeframe_Up �� ������������
   TimeframeCheck("Timeframe_Up", Timeframe_Up);
//---- �������� �������� ���������� Timeframe_Dn �� ������������ 
   TimeframeCheck("TimeframeX_Dn", TimeframeX_Dn);
//---- �������� �������� ���������� Timeframe_Dn �� ������������ 
   TimeframeCheck("Timeframe_Dn", Timeframe_Dn);
//---- ������������� ����������             
   MinBarX_Up = 1 + 7;
   MinBar_Up = 4 + 39 + 30;
   MinBarX_Dn = 1 + 7;
   MinBar_Dn = 4 + 39 + 30;                                       
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
   //----+ ���������� ��������� ����������
   int    bar;
   double Mov[3], dMov12, dMov23, Mama1, Fama1;
   //----+ ���������� ����������� ����������
   static double TrendX_Up, TrendX_Dn, TrendY_Up, TrendY_Dn;
   static int LastBars_Up, LastBars_Dn, LastBarsX_Up, LastBarsX_Dn;
   static int LastBarsY_Up, LastBarsY_Dn;
   static bool BUY_Sign, BUY_Stop, SELL_Sign, SELL_Stop;
   static datetime LastOpenTime_Up, LastOpenTime_Dn;
   
   
   //----+ +---------------------------------------------------------------+
   //----++ ��� ��� ������� �������                                        |
   //----+ +---------------------------------------------------------------+
   if (Test_Up) 
    {
      int IBARS_Up = iBars(NULL, Timeframe_Up);
      int IBARSX_Up = iBars(NULL, TimeframeX_Up);
      int IBARSY_Up = iBars(NULL, TimeframeY_Up);
      
      if (IBARS_Up >= MinBar_Up 
                && IBARSX_Up >= MinBarX_Up 
                          && IBARSY_Up >= MinBarY_Up)
       {       
         //----+ +----------------------+
         //----+ ����������� ������     |
         //----+ +----------------------+
         if (LastBarsX_Up != IBARSX_Up)
          {
           //----+ ������������� ���������� 
           LastBarsX_Up = IBARSX_Up;
           BUY_Stop = false;
           
           //----+ ���������� ������������ ��������
           Fama1 = iCustom(NULL, TimeframeX_Up, 
                    "MAMA_NK", FastLimitX_Up, SlowLimitX_Up, IPCX_Up, 0, 1);
           //---         
           Mama1 = iCustom(NULL, TimeframeX_Up, 
                    "MAMA_NK", FastLimitX_Up, SlowLimitX_Up, IPCX_Up, 1, 1);
           //----+ ����������� ������                                 
           TrendX_Up = Mama1 - Fama1;
           //----+ ����������� ������� ��� ���������� ������
           if (TrendX_Up < 0)
                      BUY_Stop = true;                                      
          }
         
         //----+ +----------------------------------------+
         //----+ ����������� �������� ��� ����� � �����   |
         //----+ +----------------------------------------+
         if (LastBars_Up != IBARS_Up)
          {
           //----+ ������������� ���������� 
           BUY_Sign = false;
           LastBars_Up = IBARS_Up;
           LastOpenTime_Up =
                     iTime(NULL, Timeframe_Up, 0) + 0.9 * Timeframe_Up; 
           
           //----+ ���������� ������������ �������� � �������� �� � �����      
           for(bar = 1; bar <= 3; bar++)
                     Mov[bar - 1]=                  
                         iCustom(NULL, Timeframe_Up, 
                                "JFatl", Length_Up, Phase_Up, 
                                                   0, IPC_Up, 0, bar);
           
           //----+ ����������� �������� ��� ������   
           dMov12 = Mov[0] - Mov[1];
           dMov23 = Mov[1] - Mov[2]; 
            
           if (TrendX_Up > 0)                     
              if (dMov23 < 0)
                if (dMov12 > 0)
                        BUY_Sign = true;                                    
          }
          
         //----+ +----------------------------------------+
         //----+ ��������� �������� ��� ����� � �����     |
         //----+ +----------------------------------------+
         if (LastBarsY_Up != IBARSY_Up)
          {
           //----+ ������������� ���������� 
           LastBarsY_Up = IBARSY_Up;
           
           //----+ ���������� ������������ �������� � �������� �� � �����      
           for(bar = 1; bar < 3; bar++)
                     Mov[bar - 1]=                  
                         iCustom(NULL, TimeframeY_Up, 
                                "JFatl", LengthY_Up, PhaseY_Up, 
                                                   0, IPCY_Up, 0, bar);
           
           //----+ ����������� �������� ��� ������   
           TrendY_Up = Mov[0] - Mov[1];                    
          }
         
         //----+ +-------------------+
         //----+ ���������� ������   |
         //----+ +-------------------+
         if (TrendY_Up > 0 || 
            TimeCurrent() >= LastOpenTime_Up)
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
      int IBARSY_Dn = iBars(NULL, TimeframeY_Dn);
      
      if (IBARS_Dn >= MinBar_Dn 
                && IBARSX_Dn >= MinBarX_Dn
                          && IBARSY_Dn >= MinBarY_Dn)
       {
         //----+ +----------------------+
         //----+ ����������� ������     |
         //----+ +----------------------+
         if (LastBarsX_Dn != IBARSX_Dn)
          {
           //----+ ������������� ���������� 
           LastBarsX_Dn = IBARSX_Dn;
           SELL_Stop = false;
           
           //----+ ���������� ������������ ��������
           Fama1 = iCustom(NULL, TimeframeX_Dn, 
                    "MAMA_NK", FastLimitX_Dn, SlowLimitX_Dn, IPCX_Dn, 0, 1);
           //---         
           Mama1 = iCustom(NULL, TimeframeX_Dn, 
                    "MAMA_NK", FastLimitX_Dn, SlowLimitX_Dn, IPCX_Dn, 1, 1);
           //----+ ����������� ������                                 
           TrendX_Dn = Mama1 - Fama1;
           //----+ ����������� ������� ��� ���������� ������
           if (TrendX_Dn > 0)
                      SELL_Stop = true;                                      
          }
         
         //----+ +----------------------------------------+
         //----+ ����������� �������� ��� ����� � �����   |
         //----+ +----------------------------------------+
         if (LastBars_Dn != IBARS_Dn)
          {
           //----+ ������������� ���������� 
           SELL_Sign = false;
           LastBars_Dn = IBARS_Dn;
           LastOpenTime_Dn = 
                     iTime(NULL, Timeframe_Dn, 0) + 0.9 * Timeframe_Dn;
           
           //----+ ���������� ������������ �������� � �������� �� � �����     
           for(bar = 1; bar <= 3; bar++)
                     Mov[bar - 1]=                  
                         iCustom(NULL, Timeframe_Dn, 
                                "JFatl", Length_Dn, Phase_Dn, 
                                                   0, IPC_Dn, 0, bar);
           
           //----+ ����������� �������� ��� ������   
           dMov12 = Mov[0] - Mov[1];
           dMov23 = Mov[1] - Mov[2]; 
            
           if (TrendX_Dn < 0)                                 
              if (dMov23 > 0)
                if (dMov12 < 0)
                       SELL_Sign = true;                                         
          }
         
         //----+ +----------------------------------------+
         //----+ ��������� �������� ��� ����� � �����     |
         //----+ +----------------------------------------+
         if (LastBarsY_Dn != IBARSY_Dn)
          {
           //----+ ������������� ���������� 
           LastBarsY_Dn = IBARSY_Dn;
           
           //----+ ���������� ������������ �������� � �������� �� � �����      
           for(bar = 1; bar < 3; bar++)
                     Mov[bar - 1]=                  
                         iCustom(NULL, TimeframeY_Dn, 
                                "JFatl", LengthY_Dn, PhaseY_Dn, 
                                                   0, IPCY_Dn, 0, bar);
           
           //----+ ����������� �������� ��� ������   
           TrendY_Dn = Mov[0] - Mov[1];                   
          }
          
         //----+ +-------------------+
         //----+ ���������� ������   |
         //----+ +-------------------+
         if (TrendY_Dn < 0 || 
            TimeCurrent() >= LastOpenTime_Dn)
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