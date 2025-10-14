//+------------------------------------------------------------------+
//|                                  TelegramSignalTrader.mq4 |
//|                                  Copyright 2023, tradeadviser Llc. |
//|                                             https://www.tradeadviser.org |
//+------------------------------------------------------------------+
#property copyright "Copyright 2023, Sopotek ,inc."
#property link      "https://github.com/nguemechieu/TelegramSignalTrader"
#property strict
//+------------------------------------------------------------------+
#define EXPERT_NAME     "TelegramSignalTrader"
#define version  "2.01"

#property tester_file "trade.csv"    // file with the data to be read by an Expert Advisor TradeExpert_file "trade.csv"    // file with the data to be read by an Expert Advisor
#property tester_library "Libraries"
#property stacksize 1000000
#property description "This is a very interactive smartBot. It uses multiples indicators base on  define strategy to get trade signals a"
#property description "nd open orders. It also integrate news filter to allow you to trade base on news events. In addition the ea generate s"
#property description "signals with screenshot on telegram or others withoud using dll import.This  give ea ability to trade on your vps witho"
#property description "ut restrictions."
#property description "This Bot will can trade generate ,manage and generate trading signals on telegram channel"





#include <DiscordTelegram/CMybot.mqh>

//+------------------------------------------------------------------+
//|   OnInit                                                         |
//+------------------------------------------------------------------+
int OnInit()
  {
//Verify license
//if ( !CheckLicense()){
//return false;
//}
   ChartColorSet();
   if(TradeDays() && SET_TRADING_DAYS == yes)
     {
      MessageBox("TIME REACHED!PLEASE WAIT FOR NEW TRADING SESSION");
      return INIT_FAILED;
     }
//---
   run_mode = GetRunMode();
//--- stop working in tester
   if(run_mode != RUN_LIVE)
     {
      PrintError(ERR_RUN_LIMITATION, InpLanguage);
      return(INIT_FAILED);
     }
   int y = 40;
   if(ChartGetInteger(0, CHART_SHOW_ONE_CLICK))
      y = 120;
   comment.Create("myPanel", 19, y);
   comment.SetColor(clrDimGray, clrGreen, 223);
//--- set language
   bot.Language(InpLanguage);
//--- set token
   init_error = bot.Token(InpToken);
//--- set filter
   bot.UserNameFilter(InpUserNameFilter);
//--- set templates
   bot.Templates(InpTemplates);
//--- set timer
   int timer_ms = 3000;
   switch(InpUpdateMode)
     {
      case UPDATE_FAST:
         timer_ms = 1000;
         break;
      case UPDATE_NORMAL:
         timer_ms = 2000;
         break;
      case UPDATE_SLOW:
         timer_ms = 3000;
         break;
      default:
         timer_ms = 3000;
         break;
     };
   EventSetMillisecondTimer(timer_ms);
   OnTimer();
//--- done
   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//|   OnDeinit                                                       |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
//---
   if(reason == REASON_CLOSE ||
      reason == REASON_PROGRAM ||
      reason == REASON_PARAMETERS ||
      reason == REASON_REMOVE ||
      reason == REASON_RECOMPILE ||
      reason == REASON_ACCOUNT ||
      reason == REASON_INITFAILED)
     {
      time_check = 0;
      comment.Destroy();
     }
//---
   EventKillTimer();
   OnDeinit3(reason);
   ChartRedraw();
  }


//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
bool Cross(int i, bool condition) //returns true if "condition" is true and was false in the previous call
  {
   bool ret = condition && !crossed[i];
   crossed[i] = condition;
   return(ret);
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
int myOrderSend(string sym, int type, double price, double volume, string ordername) //send order, return ticket ("price" is irrelevant for market orders)
  {
   long chatId = ChatID;
   if(!IsTradeAllowed())
      return(-1);
   int ticket = -1;
   int retries = 0;
   int err = 0;
   int long_trades = TradesCount(OP_BUY);
   int short_trades = TradesCount(OP_SELL);
   int long_pending = TradesCount(OP_BUYLIMIT) + TradesCount(OP_BUYSTOP);
   int short_pending = TradesCount(OP_SELLLIMIT) + TradesCount(OP_SELLSTOP);
   string ordername_ = ordername;
   if(ordername != "")
      ordername_ = "(" + ordername + ")";
//test Hedging
   if(!Hedging && ((type % 2 == 0 && short_trades + short_pending > 0) || (type % 2 == 1 && long_trades + long_pending > 0)))
     {
      myAlert(sym, "print", "Order" + ordername_ + " not sent, hedging not allowed");
      bot.SendMessage(ChatID, "Order" + ordername_ + "not sent, hedging not allowed");
      return(-1);
     }
//test maximum trades
   if((type % 2 == 0 && long_trades >= MaxLongTrades)
      || (type % 2 == 1 && short_trades >= MaxShortTrades)
      || (long_trades + short_trades >= MaxOpenTrades)
      || (type > 1 && type % 2 == 0 && long_pending >= MaxLongPendingOrders)
      || (type > 1 && type % 2 == 1 && short_pending >= MaxShortPendingOrders)
      || (type > 1 && long_pending + short_pending >= MaxPendingOrders)
     )
     {
      myAlert(sym, "print", "Order" + ordername_ + " not sent, maximum reached");
      bot.SendMessage(chatId, "Order" + ordername_ + " not sent, maximum reached");
      return(-1);
     }
   double SL = 0, TP = 0;
//prepare to send order
   while(IsTradeContextBusy())
      Sleep(100);
   RefreshRates();
   if(type == OP_BUY || type == OP_BUYLIMIT || type == OP_BUYSTOP)
     {
      price = MarketInfo(sym, MODE_ASK);
      SL = price - stoploss * MarketInfo(sym, MODE_POINT);
      TP = price + takeprofit * MarketInfo(sym, MODE_POINT);
     }
   else
      if(type == OP_SELL || type == OP_SELLLIMIT || type == OP_SELLSTOP)
        {
         price =  price = MarketInfo(sym, MODE_BID);
         SL = price + stoploss * MarketInfo(sym, MODE_POINT);
         TP = price - takeprofit * MarketInfo(sym, MODE_POINT);
        }
      else
         if(price < 0) //invalid price for pending order
           {
            myAlert(sym, "order", "Order" + ordername_ + " not sent, invalid price for pending order");
            bot.SendMessage(ChatID, "Order" + ordername_ + " not sent, invalid price for pending order");
            return(-1);
           }
   int clr = (type % 2 == 1) ? clrWhite : clrGold;
   while(ticket < 0 && retries < OrderRetry + 1)
     {
      LotDigits = (int)MarketInfo(sym, MODE_LOTSIZE);
      ticket = OrderSend(sym, type,
                         NormalizeDouble(volume, LotDigits),
                         NormalizeDouble(price, (int)MarketInfo(sym, MODE_DIGITS))
                         ,
                         MaxSlippage,
                         SL, TP,
                         ordername,
                         MagicNumber,
                         0, clr);
      if(ticket < 0)
        {
         err = GetLastError();
         myAlert(sym, "print", "OrderSend" + ordername_ + " error #" + IntegerToString(err) + " " + ErrorDescription(err));
         Sleep(OrderWait * 1000);
        }
      if(ticket < 0)
        {
         myAlert(sym, "error", "OrderSend" + ordername_ + " failed " + IntegerToString(OrderRetry + 1) + " times; error #" + IntegerToString(err) + " " + ErrorDescription(err));
         bot.SendMessage(ChatID, "OrderSend" + ordername_ + " failed " + IntegerToString(OrderRetry + 1) + " times; error #" + IntegerToString(err) + " " + ErrorDescription(err));
         return(-1);
        }
      string typestr[6] = {"Buy", "Sell", "Buy Limit", "Sell Limit", "Buy Stop", "Sell Stop"};
      myAlert(sym, "order", "Order sent" + ordername_ + ": " + typestr[type] + " " + sym + " Magic #" + IntegerToString(MagicNumber));
      bot.SendMessage(ChatID, "Order sent" + ordername_ + ": " + typestr[type] + sym + " " + (string)MagicNumber + " " + IntegerToString(MagicNumber));
      retries++;
     }
   return ticket;
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
int myOrderModify(string sym, int ticket, double SL, double TP) //modify SL and TP (absolute price), zero targets do not modify
  {
   if(!IsTradeAllowed())
      return(-1);
   bool success = false;
   int retries = 0;
   int err = 0;
   SL = stoploss;
   TP = takeprofit;
   SL = NormalizeDouble(SL, (int)MarketInfo(sym, MODE_DIGITS));
   TP =  NormalizeDouble(TP, (int)MarketInfo(sym, MODE_DIGITS));
   if(SL < 0)
      SL = 0;
   if(TP < 0)
      TP = 0;
//prepare to select order
   while(IsTradeContextBusy())
      Sleep(100);
   if(!OrderSelect(ticket, SELECT_BY_TICKET, MODE_TRADES))
     {
      err = GetLastError();
      myAlert(sym, "error", "OrderSelect failed; error #" + IntegerToString(err) + " " + ErrorDescription(err));
      bot.SendMessage(ChatID, "OrderSelect failed; error #" + IntegerToString(err) + " " + ErrorDescription(err));
      return(-1);
     }
//prepare to modify order
   while(IsTradeContextBusy())
      Sleep(100);
   RefreshRates();
   if(CompareDoubles(SL, 0))
      SL = OrderStopLoss(); //not to modify
   if(CompareDoubles(TP, 0))
      TP = OrderTakeProfit(); //not to modify
   if(CompareDoubles(SL, OrderStopLoss()) && CompareDoubles(TP, OrderTakeProfit()))
      return(0); //nothing to do
   while(!success && retries < OrderRetry + 1)
     {
      success = OrderModify(ticket,
                            NormalizeDouble(OrderOpenPrice(),
                                            (int) MarketInfo(sym, MODE_DIGITS)),
                            NormalizeDouble(SL, (int) MarketInfo(sym, MODE_DIGITS)),
                            NormalizeDouble(TP, (int) MarketInfo(sym, MODE_DIGITS)), OrderExpiration(), CLR_NONE);
      if(!success)
        {
         err = GetLastError();
         myAlert(sym, "print", "OrderModify error #" + IntegerToString(err) + " " + ErrorDescription(err));
         bot.SendMessage(ChatID, "OrderModify error #" + IntegerToString(err) + " " + ErrorDescription(err));
         Sleep(OrderWait * 1000);
        }
      retries++;
     }
   if(!success)
     {
      myAlert(sym, "error", "OrderModify failed " + IntegerToString(OrderRetry + 1) + " times; error #" + IntegerToString(err) + " " + ErrorDescription(err));
      bot.SendMessage(ChatID, "OrderModify failed " + IntegerToString(OrderRetry + 1) + " times; error #" + IntegerToString(err) + " " + ErrorDescription(err));
      return(-1);
     }
   string alertstr = "Order modified: ticket=" + IntegerToString(ticket);
   if(!CompareDoubles(SL, 0))
      alertstr = alertstr + " SL=" + DoubleToString(SL);
   if(!CompareDoubles(TP, 0))
      alertstr = alertstr + " TP=" + DoubleToString(TP);
   myAlert(sym, "modify", alertstr);
   bot.SendMessage(ChatID, "Modify " + alertstr);
   return(0);
  }

//+------------------------------------------------------------------+
//|   OnChartEvent                                                   |
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
  {
   comment.OnChartEvent(id, lparam, dparam, sparam);
  }
//+------------------------------------------------------------------+
//|   OnTimer                                                        |
//+------------------------------------------------------------------+
void OnTimer()
  {
 
//--- show init error
   if(init_error != 0)
     {
      //--- show error on display
      CustomInfo info;
      GetCustomInfo(info, init_error, InpLanguage);
      //---
      comment.Clear();
      comment.SetText(0, StringFormat("%s v.%s", EXPERT_NAME, version), CAPTION_COLOR);
      comment.SetText(1, info.text1, LOSS_COLOR);
      if(info.text2 != "")
         comment.SetText(2, info.text2, LOSS_COLOR);
      comment.Show();
      return;
     }
//--- show web error
   if(run_mode == RUN_LIVE)
     {
      //--- check bot registration
      if(time_check < TimeLocal() - PeriodSeconds(PERIOD_H1))
        {
         time_check = TimeLocal();
         if(TerminalInfoInteger(TERMINAL_CONNECTED))
           {
            //---
            web_error = bot.GetMe();
            if(web_error != 0)
              {
               //---
               if(web_error == ERR_NOT_ACTIVE)
                 {
                  time_check = TimeCurrent() - PeriodSeconds(PERIOD_H1) + 300;
                 }
               //---
               else
                 {
                  time_check = TimeCurrent() - PeriodSeconds(PERIOD_H1) + 5;
                 }
              }
            if(Move_TP_to_Breakeven)
               timelockaction();
           }
         else
           {
            web_error = ERR_NOT_CONNECTED;
            time_check = 0;
           }
        }
      //--- show error
      if(web_error != 0)
        {
         comment.Clear();
         comment.SetText(0, StringFormat("%s v.%s", EXPERT_NAME, version), CAPTION_COLOR);
         if(
#ifdef __MQL4__ web_error==ERR_FUNCTION_NOT_CONFIRMED #endif
#ifdef __MQL5__ web_error==ERR_FUNCTION_NOT_ALLOWED #endif
         )
           {
            time_check = 0;
            CustomInfo info = {0};
            GetCustomInfo(info, web_error, InpLanguage);
            comment.SetText(1, info.text1, LOSS_COLOR);
            comment.SetText(2, info.text2, LOSS_COLOR);
           }
         else
            comment.SetText(1, GetErrorDescription(web_error, InpLanguage), LOSS_COLOR);
         comment.Show();
         return;
        }
     }
//---
   bot.GetUpdates();
//---
   if(run_mode == RUN_LIVE)
     {
      comment.Clear();
      comment.SetText(0, StringFormat("%s v.%s", EXPERT_NAME, version), CAPTION_COLOR);
      comment.SetText(1, StringFormat("%s: %s", (InpLanguage == LANGUAGE_EN) ? "Bot " : "Имя Бота", bot.Name()), CAPTION_COLOR);
      comment.SetText(2, StringFormat("%s: %d", (InpLanguage == LANGUAGE_EN) ? "Chats" : "Чаты", bot.ChatsTotal()), CAPTION_COLOR);
      comment.Show();
     }
//---
   bot.ProcessMessages();
  }


//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void OnTick()
  {
   int i =0;
     for(i = 0; i < SymbolsTotal(false);i++)
     {
      //false is used to work with all symbols
      string sym = SymbolName(i, false);
      printf("sym :" + sym + (string)i);
      
      //MOVE TP AND SL
      double TradeSize = 0, SL = stoploss, TP = takeprofit, price;
      int ticket = -1;
      for(i = 0; i <= OrdersTotal(); i++)
        {
         if(OrdersTotal() > 0 && OrderSelect(i, SELECT_BY_TICKET, MODE_TRADES) && OrderType() == OP_BUY && OrderSymbol() == sym)
           {
            price = MarketInfo(sym, MODE_ASK);
            if(price - TP > MaxTP)
               TP = price - MaxTP;
            if(price - TP < MinTP)
               TP = price - MinTP;
            myOrderModify(sym, ticket, SL, 0);
            myOrderModify(sym, ticket, 0, TP);
           }
         if(OrdersTotal() > 0 && OrderSelect(i, SELECT_BY_TICKET, MODE_TRADES) && OrderType() == OP_SELL && sym == OrderSymbol())
           {
            price = MarketInfo(sym, MODE_BID);
            if(price - TP < MinTP)
               TP = price - MinTP;
            //not autotrading => only send alert
            myOrderModify(sym, ticket, SL, 0);
            myOrderModify(sym, ticket, 0, TP);
           }
        }
     }
  }






int GridError;




//+------------------------------------------------------------------+
//| Candle Time Left / Spread                                        |
//+------------------------------------------------------------------+
void SymbolInfo(string sym)
  {
//---
   string TimeLeft = TimeToStr(Time[0] + Period() * 60 - (int)TimeCurrent(), TIME_MINUTES | TIME_SECONDS);
   string Spread = DoubleToStr(MarketInfo(sym, MODE_SPREAD) / Factor, 1);
   double DayClose = iClose(sym, PERIOD_D1, 1);
   if(DayClose != 0)
     {
      double Strength = ((MarketInfo(sym, MODE_BID) - DayClose) / DayClose) * 100;
      string Label = "Strength " + DoubleToStr(Strength, 2) + "%" + " /Spread " + Spread + " /TimeLeft " + TimeLeft;
      ENUM_BASE_CORNER corner = 1;
      if(Corner == 1)
         corner = 3;
      string arrow = "q";
      if(Strength > 0)
         arrow = "p";
      string tooltip = StringFormat("strength:%d, spread :%d,Time :%s",
                                    Strength, Spread, TimeLeft);
      Draw(INAME + ": info", Label, InfoFontSize, "Calibri", InfoColor, corner, 200, 50, tooltip);
      Draw(INAME + ": info arrow", arrow, InfoFontSize + 4, "Wingdings 3", InfoColor, corner, 100, 50, tooltip);
     }
//---
  }
//+------------------------------------------------------------------+
//| draw event text                                                  |
//+------------------------------------------------------------------+
void Draw(string name, string label, int size, string font, color clr, ENUM_BASE_CORNER c, int x, int y, string tooltip)
  {
//---
   name = INAME + ": " + name;
   int windows = 0;
   if(AllowSubwindow && WindowsTotal() > 1)
      windows = 1;
   ObjectDelete(name);
   ObjectCreate(name, OBJ_LABEL, windows, 0, 0);
   ObjectSetText(name, label, size, font, clr);
   ObjectSet(name, OBJPROP_CORNER, c);
   ObjectSet(name, OBJPROP_XDISTANCE, x);
   ObjectSet(name, OBJPROP_YDISTANCE, y);
//--- justify text
   ObjectSet(name, OBJPROP_ANCHOR, 2);
   ObjectSetString(0, name, OBJPROP_TOOLTIP, tooltip);
   ObjectSet(name, OBJPROP_SELECTABLE, 0);
//---
  }
  

//+------------------------------------------------------------------+
//| draw vertical lines                                              |
//+------------------------------------------------------------------+
void DrawLine(string name, datetime time, color clr, string tooltip)
  {
//---
   name = INAME + ": " + name;
   ObjectDelete(name);
   ObjectCreate(name, OBJ_VLINE, 0, time, 0);
   ObjectSet(name, OBJPROP_COLOR, clr);
   ObjectSet(name, OBJPROP_STYLE, 2);
   ObjectSet(name, OBJPROP_WIDTH, 5);
   ObjectSetString(0, name, OBJPROP_TOOLTIP, tooltip);
//---
  }






//+------------------------------------------------------------------+
//| Notifications                                                    |
//+------------------------------------------------------------------+
void setAlerts(string message)
  {
//---
   if(PopupAlerts)
      Alert(message);
   if(SoundAlerts)
      PlaySound(AlertSoundFile);
   if(NotificationAlerts)
      SendNotification(message);
   if(EmailAlerts)
      SendMail("emailsignal", message);
//---
  }



//+------------------------------------------------------------------+
