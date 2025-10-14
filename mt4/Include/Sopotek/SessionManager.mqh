//+------------------------------------------------------------------+
//|                                               SessionManager.mqh |
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
bool IsTradingSession(string s1s,string s1e,string s2s,string s2e,string s3s,string s3e){
   datetime now=TimeCurrent();
   string today=TimeToString(now,TIME_DATE);
   datetime st1=StringToTime(today+" "+s1s);
   datetime en1=StringToTime(today+" "+s1e);
   datetime st2=StringToTime(today+" "+s2s);
   datetime en2=StringToTime(today+" "+s2e);
   datetime st3=StringToTime(today+" "+s3s);
   datetime en3=StringToTime(today+" "+s3e);
   if((now>=st1 && now<=en1)||(now>=st2 && now<=en2)||(now>=st3 && now<=en3)) return true;
   return false;
}
