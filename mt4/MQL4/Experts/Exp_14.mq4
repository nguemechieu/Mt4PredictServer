//+==================================================================+
//|                                                       Exp_14.mq4 |
//|                             Copyright © 2008,   Nikolay Kositsin | 
//|                              Khabarovsk,   farria@mail.redcom.ru | 
//+==================================================================+
#property copyright "Copyright © 2008, Nikolay Kositsin"
#property link "farria@mail.redcom.ru"
//----+ +---------------------------------------------------------------------------+
//---- ВХОДНЫЕ ПАРАМЕТРЫ ЭКСПЕРТА ДЛЯ BUY СДЕЛОК 
extern bool   Test_Up = true;//фильтр направления расчётов сделок
extern double Money_Management_Up = 0.1;
//----   
extern int    TimeframeX_Up = 240;                 
extern int    PeriodWATR_Up = 10; 
extern double Kwatr_Up = 1.0000; 
extern int    HighLow_Up = 0; 
//---- + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
extern int    Timeframe_Up = 60;
extern int    JJLength_Up = 8;  // глубина JJMA сглаживания входной цены
extern int    JXLength_Up = 8;  // глубина JurX сглаживания полученного индикатора 
extern int    Phase_Up = 100;// параметр, изменяющийся в пределах
                        // -100 ... +100, влияет на качество переходного процесса; 
extern int    IPC_Up = 0; /* Выбор цен, по которым производится расчёт 
индикатора (0-CLOSE, 1-OPEN, 2-HIGH, 3-LOW, 4-MEDIAN, 5-TYPICAL, 
6-WEIGHTED, 7-Heiken Ashi Close, 8-SIMPL, 9-TRENDFOLLOW, 10-0.5*TRENDFOLLOW, 
11-Heiken Ashi Low, 12-Heiken Ashi High, 13-Heiken Ashi Open, 
14-Heiken Ashi Close.) */
extern int    STOPLOSS_Up = 50;  // стоплосс
extern int    TAKEPROFIT_Up = 100; // тейкпрофит
extern bool   ClosePos_Up = true; // разрешение принудительного закрывания позиции
//----+ +---------------------------------------------------------------------------+
//---- ВХОДНЫЕ ПАРАМЕТРЫ ЭКСПЕРТА ДЛЯ SELL СДЕЛОК 
extern bool   Test_Dn = true;//фильтр направления расчётов сделок
extern double Money_Management_Dn = 0.1;
//----
extern int    TimeframeX_Dn = 240;
extern int    PeriodWATR_Dn = 10; 
extern double Kwatr_Dn = 1.0000; 
extern int    HighLow_Dn = 0; 
//---- + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
extern int    Timeframe_Dn = 60;
extern int    JJLength_Dn = 8;  // глубина JJMA сглаживания входной цены
extern int    JXLength_Dn = 8;  // глубина JurX сглаживания полученного индикатора 
extern int    Phase_Dn = 100;// параметр, изменяющийся в пределах
                        // -100 ... +100, влияет на качество переходного процесса; 
extern int    IPC_Dn = 0; /* Выбор цен, по которым производится расчёт 
индикатора (0-CLOSE, 1-OPEN, 2-HIGH, 3-LOW, 4-MEDIAN, 5-TYPICAL, 
6-WEIGHTED, 7-Heiken Ashi Close, 8-SIMPL, 9-TRENDFOLLOW, 10-0.5*TRENDFOLLOW, 
11-Heiken Ashi Low, 12-Heiken Ashi High, 13-Heiken Ashi Open, 
14-Heiken Ashi Close.) */
extern int   STOPLOSS_Dn = 50;  // стоплосс
extern int   TAKEPROFIT_Dn = 100; // тейкпрофит
extern bool   ClosePos_Dn = true; // разрешение принудительного закрывания позиции
//----+ +---------------------------------------------------------------------------+
//---- Целые переменные для минимума расчётных баров
int MinBar_Up, MinBar_Dn, MinBarX_Up, MinBarX_Dn;
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
   //---- Проверка значения переменной Timeframe на корректность
   if (Timeframe != 1)
    if (Timeframe != 5)
     if (Timeframe != 15)
      if (Timeframe != 30)
       if (Timeframe != 60)
        if (Timeframe != 240)
         if (Timeframe != 1440)
           Print(StringConcatenate("Параметр ",Name,
                     " не может ", "быть равным ", Timeframe, "!!!"));    
//----+ 
  }
//+==================================================================+
//| Custom Expert initialization function                            |
//+==================================================================+
int init()
  {
//---- Проверка значения переменной Timeframe_Up на корректность
   TimeframeCheck("TimeframeX_Up", TimeframeX_Up);
//---- Проверка значения переменной Timeframe_Up на корректность
   TimeframeCheck("Timeframe_Up", Timeframe_Up);
//---- Проверка значения переменной Timeframe_Dn на корректность 
   TimeframeCheck("TimeframeX_Dn", TimeframeX_Dn);
//---- Проверка значения переменной Timeframe_Dn на корректность 
   TimeframeCheck("Timeframe_Dn", Timeframe_Dn);
//---- Инициализация переменных             
   MinBarX_Up = 2 + PeriodWATR_Up;
   MinBar_Up = 4 + 3 * JXLength_Up + 30;
   MinBarX_Dn = 2 + PeriodWATR_Dn;
   MinBar_Dn = 4 + 3 * JXLength_Dn + 30;                                       
//---- завершение инициализации
   return(0);
  }
//+==================================================================+
//| expert deinitialization function                                 |
//+==================================================================+  
int deinit()
  {
//----+
   
    //---- Завершение деинициализации эксперта
    return(0);
//----+ 
  }
//+==================================================================+
//| Custom Expert iteration function                                 |
//+==================================================================+
int start()
  {
   //----+ Объявление локальных переменных
   int    bar;
   double JCCIX[2], Trend, Fast_StepMA, Slow_StepMA;
   //----+ Объявление статических переменных
   static double TrendX_Up, TrendX_Dn, OldTrend_Up, OldTrend_Dn;
   static int LastBars_Up, LastBars_Dn, LastBarsX_Up, LastBarsX_Dn;
   static bool BUY_Sign, BUY_Stop, SELL_Sign, SELL_Stop;
   static bool SecondStart_Up, SecondStart_Dn;
   
   //----+ +---------------------------------------------------------------+
   //----++ КОД ДЛЯ ДЛИННЫХ ПОЗИЦИЙ                                        |
   //----+ +---------------------------------------------------------------+
   if (Test_Up) 
    {
      int IBARS_Up = iBars(NULL, Timeframe_Up);
      int IBARSX_Up = iBars(NULL, TimeframeX_Up);
      
      if (IBARS_Up >= MinBar_Up && IBARSX_Up >= MinBarX_Up)
       {       
         //----+ +----------------------+
         //----+ ОПРЕДЕЛЕНИЕ ТРЕНДА     |
         //----+ +----------------------+
         if (LastBarsX_Up != IBARSX_Up)
          {
           //----+ Иницмализация переменных 
           LastBarsX_Up = IBARSX_Up;
           BUY_Sign = false;
           BUY_Stop = false;
           
           //----+ вычисление индикаторных значений
           Fast_StepMA = iCustom(NULL, TimeframeX_Up, "StepMA_Stoch_NK", 
                                 PeriodWATR_Up, Kwatr_Up, HighLow_Up, 0, 1);
           //---         
           Slow_StepMA = iCustom(NULL, TimeframeX_Up, "StepMA_Stoch_NK", 
                                 PeriodWATR_Up, Kwatr_Up, HighLow_Up, 1, 1);
           //----+ определение тренда                                 
           TrendX_Up = Fast_StepMA - Slow_StepMA;
           //----+ определение сигнала для закрывания сделок
           if (TrendX_Up < 0)
                      BUY_Stop = true;                                      
          }
         
         //----+ +----------------------------------------+
         //----+ ОПРЕДЕЛЕНИЕ СИГНАЛОВ ДЛЯ ВХОДА В РЫНОК   |
         //----+ +----------------------------------------+
         if (LastBars_Up != IBARS_Up && TrendX_Up > 0)
          {
           //----+ Иницмализация переменных 
           BUY_Sign = false;
           LastBars_Up = IBARS_Up;
           
           //----+ Инициализация нуля
           if (!SecondStart_Up)
            {
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
           
           //----+ вычисление индикаторных значений и загрузка их в буфер      
           for(bar = 1; bar < 3; bar++)
                     JCCIX[bar - 1] =                  
                         iCustom(NULL, Timeframe_Up, 
                                "JCCIX", JJLength_Up, JXLength_Up, 
                                                   Phase_Up, IPC_Up, 0, bar);
           
           //----+ определение сигналов для сделок   
           Trend = JCCIX[0] - JCCIX[1];
            
           if (TrendX_Up > 0)                     
              if (OldTrend_Up < 0)
                         if (Trend > 0)
                                 BUY_Sign = true; 
           if (Trend != 0)
                   OldTrend_Up = Trend;                                   
          }
         
         //----+ +-------------------+
         //----+ СОВЕРШЕНИЕ СДЕЛОК   |
         //----+ +-------------------+
          if (!OpenBuyOrder1(BUY_Sign, 1, Money_Management_Up, 
                                          STOPLOSS_Up, TAKEPROFIT_Up))
                                                                 return(-1);
          if (ClosePos_Up)
                if (!CloseOrder1(BUY_Stop, 1))
                                        return(-1);
        }
     }
     
   //----+ +---------------------------------------------------------------+
   //----++ КОД ДЛЯ КОРОТКИХ ПОЗИЦИЙ                                       |
   //----+ +---------------------------------------------------------------+
   if (Test_Dn) 
    {
      int IBARS_Dn = iBars(NULL, Timeframe_Dn);
      int IBARSX_Dn = iBars(NULL, TimeframeX_Dn);
      
      if (IBARS_Dn >= MinBar_Dn && IBARSX_Dn >= MinBarX_Dn)
       {
         //----+ +----------------------+
         //----+ ОПРЕДЕЛЕНИЕ ТРЕНДА     |
         //----+ +----------------------+
         if (LastBarsX_Dn != IBARSX_Dn)
          {
           //----+ Иницмализация переменных 
           LastBarsX_Dn = IBARSX_Dn;
           SELL_Sign = false;
           SELL_Stop = false;
           
           //----+ вычисление индикаторных значений
           Fast_StepMA = iCustom(NULL, TimeframeX_Dn, "StepMA_Stoch_NK", 
                                 PeriodWATR_Dn, Kwatr_Dn, HighLow_Dn, 0, 1);
           //---         
           Slow_StepMA = iCustom(NULL, TimeframeX_Dn, "StepMA_Stoch_NK", 
                                 PeriodWATR_Dn, Kwatr_Dn, HighLow_Dn, 1, 1);
           //----+ определение тренда                                 
           TrendX_Dn = Fast_StepMA - Slow_StepMA;
           //----+ определение сигнала для закрывания сделок
           if (TrendX_Dn > 0)
                      SELL_Stop = true;                                      
          }
         
         //----+ +----------------------------------------+
         //----+ ОПРЕДЕЛЕНИЕ СИГНАЛОВ ДЛЯ ВХОДА В РЫНОК   |
         //----+ +----------------------------------------+
         if (LastBars_Dn != IBARS_Dn && TrendX_Dn < 0)
          {
           //----+ Иницмализация переменных 
           SELL_Sign = false;
           LastBars_Dn = IBARS_Dn;
           
           //----+ Инициализация нуля
           if (!SecondStart_Dn)
            {
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
           
           //----+ вычисление индикаторных значений и загрузка их в буфер     
           for(bar = 1; bar < 3; bar++)
                     JCCIX[bar - 1]=                  
                         iCustom(NULL, Timeframe_Dn, 
                                "JCCIX", JJLength_Dn, JXLength_Dn, 
                                                   Phase_Dn, IPC_Dn, 0, bar);
           
           //----+ определение сигналов для сделок   
           Trend = JCCIX[0] - JCCIX[1];
            
           if (TrendX_Dn < 0)                                 
              if (OldTrend_Dn > 0)
                         if (Trend < 0)
                                 SELL_Sign = true;
           if (Trend != 0)
                   OldTrend_Dn = Trend;                                         
          }
          
         //----+ +-------------------+
         //----+ СОВЕРШЕНИЕ СДЕЛОК   |
         //----+ +-------------------+
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