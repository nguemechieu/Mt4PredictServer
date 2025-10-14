//+------------------------------------------------------------------+
//|                                                        Utils.mqh |
//|                                    Copyright 2025, Sopotek ,Inc. |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, Sopotek ,Inc."
#property link      "https://www.mql5.com"
#property strict
//+------------------------------------------------------------------+
//| defines                                                          |
//+------------------------------------------------------------------+
// #define MacrosHello   "Hello, world!"
// #define MacrosYear    2010
//+------------------------------------------------------------------+
//| DLL imports                                                      |
//+------------------------------------------------------------------+
// #import "user32.dll"
//   int      SendMessageA(int hWnd,int Msg,int wParam,int lParam);
// #import "my_expert.dll"
//   int      ExpertRecalculate(int wParam,int lParam);
// #import
//+------------------------------------------------------------------+
//| EX5 imports                                                      |
//+------------------------------------------------------------------+
// #import "stdlib.ex5"
//   string ErrorDescription(int error_code);
// #import
//+------------------------------------------------------------------+
bool IsSpreadOK(double maxSpread){
   double spread = MarketInfo(Symbol(), MODE_SPREAD)/10.0;
   return (spread <= maxSpread);
}

bool DailyLimitHit(double &profit,double &loss,double profitPct,double lossPct,datetime &tDate){
   if(tDate!=TimeDay(TimeCurrent())){
      tDate=TimeDay(TimeCurrent());
      profit=0;
      loss=0;
   }
   double bal=AccountBalance();
   double target=bal*profitPct/100.0;
   double limit=bal*lossPct/100.0;
   if(profit>=target || loss<=-limit) return true;
   return false;
}

int CountOpenTrades(int magic){
   int total=0;
   for(int i=OrdersTotal()-1;i>=0;i--){
      if(OrderSelect(i,SELECT_BY_POS,MODE_TRADES))
         if(OrderMagicNumber()==magic) total++;
   }
   return total;
}
