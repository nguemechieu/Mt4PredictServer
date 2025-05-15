//Для работы эксперта в папке Metatrader\EXPERTS\indicators небходимо 
//наличие индикаторов 5c_OsMA.mq4 и J2JMA.mq4
//+==================================================================+
//|                                                       Exp_11.mq4 |
//|                             Copyright © 2008,   Nikolay Kositsin | 
//|                              Khabarovsk,   farria@mail.redcom.ru | 
//+==================================================================+
#property copyright "Copyright © 2008, Nikolay Kositsin"
#property link "farria@mail.redcom.ru"
//----+ +--------------------------------------------------------------------------+
//---- ВХОДНЫЕ ПАРАМЕТРЫ ЭКСПЕРТА ДЛЯ BUY СДЕЛОК 
extern bool   Test_Up = true;//фильтр направления расчётов сделок
extern double Money_Management_Up = 0.1;
//---- входные параметры пользовательского индикатора J2JMA.mq4
extern int    TimeframeX_Up = 240;
extern int    Length1X_Up = 4;  // глубина первого сглаживания 
extern int    Phase1X_Up = 100; // параметр первого сглаживания, 
       //изменяющийся в пределах -100 ... +100, влияет на качество 
       //переходного процесса усреднения;  
extern int    Length2X_Up = 4;  // глубина второго сглаживания 
extern int    Phase2X_Up = 100; // параметр второго сглаживания, 
       //изменяющийся в пределах -100 ... +100, влияет на качество 
       //переходного процесса усреднения;  
extern int    IPCX_Up = 0;/* Выбор цен, по которым производится расчёт 
индикатора (0-CLOSE, 1-OPEN, 2-HIGH, 3-LOW, 4-MEDIAN, 5-TYPICAL, 
6-WEIGHTED, 7-Heiken Ashi Close, 8-SIMPL, 9-TRENDFOLLOW, 10-0.5*TRENDFOLLOW, 
11-Heiken Ashi Low, 12-Heiken Ashi High, 13-Heiken Ashi Open, 
14-Heiken Ashi Close.) */
//---- входные параметры пользовательского индикатора 5c_OsMA.mq4
extern int    Timeframe_Up = 60;
extern double IndLevel_Up = 0; // пробойный уровень индикатора
extern int    FastEMA_Up = 12;  // период быстрой EMA
extern int    SlowEMA_Up = 26;  // период медленной EMA
extern int    SignalSMA_Up = 9;  // период сигнальной SMA
extern int    STOPLOSS_Up = 50;  // стоплосс
extern int    TAKEPROFIT_Up = 100; // тейкпрофит
extern int    TRAILINGSTOP_Up = 0; // трейлинстоп
extern int    PriceLevel_Up =40; // разница между текущей ценой и 
                                         // ценой срабатывания отложенного ордера
extern bool   ClosePos_Up = true; // разрешение принудительного закрывания позиции
//----+ +--------------------------------------------------------------------------+
//---- ВХОДНЫЕ ПАРАМЕТРЫ ЭКСПЕРТА ДЛЯ SELL СДЕЛОК 
extern bool   Test_Dn = true;//фильтр направления расчётов сделок
extern double Money_Management_Dn = 0.1;
//---- входные параметры пользовательского индикатора J2JMA.mq4
extern int    TimeframeX_Dn = 240;
extern int    Length1X_Dn = 4;  // глубина сглаживания 
extern int    Phase1X_Dn = 100;  // параметр первого сглаживания, 
       //изменяющийся в пределах -100 ... +100, влияет на качество 
       //переходного процесса усреднения;  
extern int    Length2X_Dn = 4;  // глубина сглаживания 
extern int    Phase2X_Dn = 100; // параметр второго сглаживания, 
       //изменяющийся в пределах -100 ... +100, влияет на качество 
       //переходного процесса усреднения;  
extern int    IPCX_Dn = 0;/* Выбор цен, по которым производится расчёт 
индикатора (0-CLOSE, 1-OPEN, 2-HIGH, 3-LOW, 4-MEDIAN, 5-TYPICAL, 
6-WEIGHTED, 7-Heiken Ashi Close, 8-SIMPL, 9-TRENDFOLLOW, 10-0.5*TRENDFOLLOW, 
11-Heiken Ashi Low, 12-Heiken Ashi High, 13-Heiken Ashi Open, 
14-Heiken Ashi Close.) */
//---- входные параметры пользовательского индикатора 5c_OsMA.mq4
extern int    Timeframe_Dn = 60;
extern double IndLevel_Dn = 0; // пробойный уровень индикатора
extern int    FastEMA_Dn = 12;  // период быстрой EMA
extern int    SlowEMA_Dn = 26;  // период медленной EMA
extern int    SignalSMA_Dn = 9;  // период сигнальной SMA
extern int    STOPLOSS_Dn = 50;  // стоплосс
extern int    TAKEPROFIT_Dn = 100; // тейкпрофит
extern int    TRAILINGSTOP_Dn = 0; // трейлинстоп
extern int    PriceLevel_Dn = 40; // разница между текущей ценой и 
                                         // ценой срабатывания отложенного ордера
extern bool   ClosePos_Dn = true; // разрешение принудительного закрывания позиции
//----+ +--------------------------------------------------------------------------+
//---- Целые переменные для минимума расчётных баров
int MinBarX_Up, MinBar_Up, MinBarX_Dn, MinBar_Dn;
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
           Print(StringConcatenate("TimeframeCheck: Параметр ",Name,
                     " не может ", "быть равным ", Timeframe, "!!!"));    
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
//---- Проверка значения переменной Timeframe_Up на корректность
   TimeframeCheck("Timeframe_Up", Timeframe_Up); 
   //---- Проверка значения переменной TimeframeX_Up на корректность
   TimeframeCheck("TimeframeX_Up", TimeframeX_Up);                                                                        
//---- Проверка значения переменной Timeframe_Dn на корректность 
   TimeframeCheck("Timeframe_Dn", Timeframe_Dn);
   //---- Проверка значения переменной Timeframe_Dn на корректность 
   TimeframeCheck("TimeframeX_Dn", TimeframeX_Dn);    
//---- Инициализация переменных             
   MinBar_Up  = 3 + MathMax(FastEMA_Up, SlowEMA_Up) + SignalSMA_Up;
   MinBarX_Up  = 3 + 30 + 30;
   MinBar_Dn  = 3 + MathMax(FastEMA_Dn, SlowEMA_Dn) + SignalSMA_Dn;
   MinBarX_Dn  = 3 + 30 + 30;                              
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
   double J2JMA1, J2JMA2, Osc1, Osc2;
   //----+ Объявление статических переменных
   //----+ +---------------------------------------------------------------+
   static double TrendX_Up, TrendX_Dn;
   static datetime StopTime_Up, StopTime_Dn; 
   static int LastBars_Up, LastBarsX_Up, LastBarsX_Dn, LastBars_Dn;
   static bool BUY_Sign, BUY_Stop, SELL_Sign, SELL_Stop;
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
           BUY_Stop = false;
           
           //----+ вычисление индикаторных значений для J2JMA   
           J2JMA1 = iCustom(NULL, TimeframeX_Up, 
                                "J2JMA", Length1X_Up, Length2X_Up,
                                             Phase1X_Up, Phase2X_Up,  
                                                     0, IPCX_Up, 0, 1);
           //---                     
           J2JMA2 = iCustom(NULL, TimeframeX_Up, 
                                "J2JMA", Length1X_Up, Length2X_Up,
                                             Phase1X_Up, Phase2X_Up,  
                                                     0, IPCX_Up, 0, 2);
           
           //----+ определение тренда                                 
           TrendX_Up = J2JMA1 - J2JMA2;
           //----+ определение сигнала для закрывания сделок
           if (TrendX_Up < 0)
                      BUY_Stop = true;                                      
          }
          
         //----+ +----------------------------------------+
         //----+ ОПРЕДЕЛЕНИЕ СИГНАЛОВ ДЛЯ ВХОДА В РЫНОК   |
         //----+ +----------------------------------------+
         if (LastBars_Up != IBARS_Up)
          {
           //----+ Иницмализация переменных 
           BUY_Sign = false;
           LastBars_Up = IBARS_Up;
           StopTime_Up = iTime(NULL, Timeframe_Up, 0)
                                          + 60 * Timeframe_Up;
           //----+ вычисление индикаторных значений
           Osc1 = iCustom(NULL, Timeframe_Up, 
                         "5c_OsMA", FastEMA_Up, SlowEMA_Up,
                                               SignalSMA_Up, 5, 1);
           //---                   
           Osc2 = iCustom(NULL, Timeframe_Up, 
                         "5c_OsMA", FastEMA_Up, SlowEMA_Up,
                                               SignalSMA_Up, 5, 2);
           
           //----+ определение сигналов для сделок
           if (TrendX_Up > 0)                                           
            if (Osc2 < IndLevel_Up)
             if (Osc1 > IndLevel_Up)
                        BUY_Sign = true;                               
          }
          
         //----+ +-------------------+
         //----+ СОВЕРШЕНИЕ СДЕЛОК   |
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
           //--- Иницмализация переменных 
           LastBarsX_Dn = IBARSX_Dn;
           SELL_Stop = false;
           
           //----+ вычисление индикаторных значений для J2JMA   
           J2JMA1 = iCustom(NULL, TimeframeX_Dn, 
                                "J2JMA", Length1X_Dn, Length2X_Dn,
                                             Phase1X_Dn, Phase2X_Dn,  
                                                     0, IPCX_Dn, 0, 1);
           //---                     
           J2JMA2 = iCustom(NULL, TimeframeX_Dn, 
                                "J2JMA", Length1X_Dn, Length2X_Dn,
                                             Phase1X_Dn, Phase2X_Dn,  
                                                     0, IPCX_Dn, 0, 2);
           
           //----+ определение тренда                                 
           TrendX_Dn = J2JMA1 - J2JMA2;
           //----+ определение сигнала для закрывания сделок
           if (TrendX_Dn > 0)
                      SELL_Stop = true;                                      
          }
         
         //----+ +----------------------------------------+
         //----+ ОПРЕДЕЛЕНИЕ СИГНАЛОВ ДЛЯ ВХОДА В РЫНОК   |
         //----+ +----------------------------------------+
         if (LastBars_Dn != IBARS_Dn)
          {
           //----+ Иницмализация переменных 
           SELL_Sign = false;
           LastBars_Dn = IBARS_Dn;
           StopTime_Dn = iTime(NULL, Timeframe_Dn, 0)
                                          + 60 * Timeframe_Dn;
           //----+ вычисление индикаторных значений    
           Osc1 = iCustom(NULL, Timeframe_Dn, 
                         "5c_OsMA", FastEMA_Dn, SlowEMA_Dn,
                                               SignalSMA_Dn, 5, 1);
           //---                   
           Osc2 = iCustom(NULL, Timeframe_Dn, 
                         "5c_OsMA", FastEMA_Dn, SlowEMA_Dn,
                                               SignalSMA_Dn, 5, 2);
           
           //----+ определение сигналов для сделок
           if (TrendX_Dn < 0)                                           
            if (Osc2 > IndLevel_Dn)
             if (Osc1 < IndLevel_Dn)
                        SELL_Sign = true;                               
          }
          
         //----+ +-------------------+
         //----+ СОВЕРШЕНИЕ СДЕЛОК   |
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
//+------------------------------------------------------------------+