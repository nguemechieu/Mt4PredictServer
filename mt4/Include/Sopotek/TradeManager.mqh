//+------------------------------------------------------------------+
//|                                                 TradeManager.mqh |
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
void OpenTrade(int type,double lot,int magic,string comment,double commission,bool useReversal){
   double sl,tp;
   if(type==OP_BUY){
      sl=Bid-50*Point; tp=Bid+100*Point;
      int df=OrderSend(Symbol(),OP_BUY,lot,Ask,3,sl,tp,comment,magic,0,clrGreen);
   } else {
      sl=Ask+50*Point; tp=Ask-100*Point;
      int fi=OrderSend(Symbol(),OP_SELL,lot,Bid,3,sl,tp,comment,magic,0,clrRed);
   }
}

void ManageOpenTrades(int magic,double BEtrig,double BEoff,double TP1,double TP2,double TP3,double trail){
   for(int i=OrdersTotal()-1;i>=0;i--){
      if(OrderSelect(i,SELECT_BY_POS,MODE_TRADES)){
         if(OrderMagicNumber()!=magic) continue;
         double profit=OrderProfit()+OrderCommission()+OrderSwap();
         double distance=0;
         if(OrderType()==OP_BUY){
            distance=(Bid-OrderOpenPrice())/Point;
            if(distance>=BEtrig) int mod1=OrderModify(OrderTicket(),OrderOpenPrice()+BEoff*Point,0,OrderTakeProfit(),0,clrAqua);
         }
         if(OrderType()==OP_SELL){
            distance=(OrderOpenPrice()-Ask)/Point;
            if(distance>=BEtrig) int ghj=OrderModify(OrderTicket(),OrderOpenPrice()-BEoff*Point,0,OrderTakeProfit(),0,clrAqua);
         }
         // trailing logic
         if(distance>=TP1) {
            double newSL=(OrderType()==OP_BUY)? Bid - trail*Point : Ask + trail*Point;
           int mod= OrderModify(OrderTicket(),OrderOpenPrice(),newSL,OrderTakeProfit(),0,clrYellow);
         }
      }
   }
}
