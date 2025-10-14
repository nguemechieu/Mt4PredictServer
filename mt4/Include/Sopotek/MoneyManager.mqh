//+------------------------------------------------------------------+
//|                                                 MoneyManager.mqh |
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
double CalcLotSize(bool useAuto,double lotCapital,double fixedLot){
   if(!useAuto) return fixedLot;
   double lot = AccountFreeMargin() / lotCapital * 0.01;
   lot = MathMax(MarketInfo(Symbol(),MODE_MINLOT),lot);
   lot = NormalizeDouble(lot,2);
   return lot;
}
