//+------------------------------------------------------------------+
//|                     Mt4PredictorServer.mq4                       |
//| AI-powered Trading with DLL machine learning prediction          |
//+------------------------------------------------------------------+
#property strict

// === Inputs ===
input double RiskPercent       = 3.5;
input double StopLossPips      = 50.0;
input double TakeProfitPips    = 40.0;
input double ConfidenceMin     = 0.7;
input double ProfitTargetPercent = 1.5;
input int MaxTradeMinutes      = 180;
input string TradeSymbols      = "EURUSD,GBPUSD,USDCAD,USDJPY,EURJPY";
input color BackgroundColor    = clrBlack;

// === DLL Import ===
#import "PredictBridge.dll"
void SendIndicatorSignal(double s1, double s2, double s3, double s4, const char &symbol[], int time,
                         double open, double close, double high, double low, int volume,
                         uchar &result[], int resultSize);

void SendCandleBatch(const uchar &ssinput[], int inputSize, uchar &output[], int outputSize);
void GetAccountInfo(char &result[], int resultSize);
void GetOpenPositions(char &result[], int resultSize);

void GetCommand(uchar &result[], int size);
#import


// === Globals ===

uchar accountBuf[2048];
uchar positionBuf[4096];

int tradeCount = 0;
double lastProfit = 0;
string lastSymbol = "";
string lastSignal = "";
double lastConfidence = 0;
bool TradingPaused = false;
uchar buffer[128];


void FetchAndLogOpenPositions() {
   GetOpenPositions(positionBuf, ArraySize(positionBuf));
   string positions = CharArrayToString(positionBuf);
   Print("📂 Open Positions:\n", positions);
}

// === Utility ===
string StringTrim(string text) {
   return StringTrimRight(StringTrimLeft(text));
}
string SerializeCandles(string symbol, int count) {
   string result = "";
   int total = MathMin(count, iBars(symbol, 0) - 1);
   for (int i = total; i >= 1; i--) {
      int time = (int)iTime(symbol, 0, i);
      double open = iOpen(symbol, 0, i);
      double close = iClose(symbol, 0, i);
      double high = iHigh(symbol, 0, i);
      double low = iLow(symbol, 0, i);
      int volume = (int)iVolume(symbol, 0, i);

      result += StringFormat("%d,%.5f,%.5f,%.5f,%.5f,%d;", time, open, close, high, low, volume);
   }
   return result;
}
void FetchAndSendAccountInfo() {
   // Build account info string
   string payload = StringFormat(
      "account:Balance=%.2f,Equity=%.2f,Margin=%.2f,FreeMargin=%.2f,Leverage=%d,AccountName=%s,AccountNumber=%d,Currency=%s,Broker=%s",
      AccountBalance(),
      AccountEquity(),
      AccountMargin(),
      AccountFreeMargin(),
      (int)AccountLeverage(),
      AccountName(),
      AccountNumber(),
      AccountCurrency(),
      AccountCompany()
   );

   // Convert to uchar buffer
   uchar sendBuf[1024];
   uchar recvBuf[1024];
   StringToCharArray(payload, sendBuf);

   // Reuse the same sending function (bridge command system)
   SendCandleBatch(sendBuf, ArraySize(sendBuf), recvBuf, ArraySize(recvBuf));

   // Optionally log the response
   string response = CharArrayToString(recvBuf);
   Print("📤 Sent Account Info | Server Response: ", response);
}
void FetchAndSendPositions() {
   string payload = "positions:";

   // === Open Trades ===
   for (int i = 0; i < OrdersTotal(); i++) {
      if (OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) {
         if (OrderType() == OP_BUY || OrderType() == OP_SELL) {
            string type = (OrderType() == OP_BUY) ? "Buy" : "Sell";
            string line = StringFormat(
               "OPEN,%d,%s,%s,%.2f,%.5f,%.5f,%.5f,%.2f,%s;",
               OrderTicket(),
               OrderSymbol(),
               type,
               OrderLots(),
               OrderOpenPrice(),
               OrderStopLoss(),
               OrderTakeProfit(),
               OrderProfit(),
               TimeToString(OrderOpenTime(), TIME_DATE | TIME_MINUTES)
            );
            payload += line;
         }
      }
   }

   // === Closed Trades (History within last 7 days) ===
   datetime from = TimeCurrent() - 7 * 24 * 60 * 60;
   datetime to = TimeCurrent();
   int total = OrdersHistoryTotal();

   for (int i = 0; i < total; i++) {
      if (OrderSelect(i, SELECT_BY_POS, MODE_HISTORY)) {
         if (OrderCloseTime() >= from && (OrderType() == OP_BUY || OrderType() == OP_SELL)) {
            string type = (OrderType() == OP_BUY) ? "Buy" : "Sell";
            string line = StringFormat(
               "CLOSED,%d,%s,%s,%.2f,%.5f,%.5f,%.5f,%.2f,%s;",
               OrderTicket(),
               OrderSymbol(),
               type,
               OrderLots(),
               OrderOpenPrice(),
               OrderStopLoss(),
               OrderTakeProfit(),
               OrderProfit(),
               TimeToString(OrderCloseTime(), TIME_DATE | TIME_MINUTES)
            );
            payload += line;
         }
      }
   }

   // === Send to server ===
   if (StringLen(payload) == 9) {
      Print("⚠️ No open or closed positions found.");
      return;
   }

   uchar sendBuf[4096];
   uchar recvBuf[1024];
   StringToCharArray(payload, sendBuf);
   SendCandleBatch(sendBuf, ArraySize(sendBuf), recvBuf, ArraySize(recvBuf));

   string response = CharArrayToString(recvBuf);
   Print("📤 Sent Position Data (Open + Closed) | Server Response: ", response);
}

//+------------------------------------------------------------------+
int OnInit() {
   ChartSetInteger(0, CHART_COLOR_BACKGROUND, BackgroundColor);
   CreateInfoBox();
   Print("✅ PredictorEA initialized.");
   FetchAndSendAccountInfo();
   FetchAndSendPositions();

   string symbols[];
   int symbolCount = StringSplit(TradeSymbols, ',', symbols);
   int candleLimit = 100;  // You can adjust this to fetch more/less candles
    for (int i = 0; i < symbolCount; i++) {
      string symbol = StringTrim(symbols[i]);
      if (symbol == "") continue;

      int totalBars = iBars(symbol, PERIOD_CURRENT);
      int limit = MathMin(candleLimit, totalBars - 1);  // exclude current forming candle

      for (int j = limit; j >= 1; j--) {
         double s1 = iRSI(symbol, 0, 14, PRICE_CLOSE, j);
         double s2 = iMA(symbol, 0, 12, 0, MODE_EMA, PRICE_CLOSE, j);
         double s3 = iMA(symbol, 0, 26, 0, MODE_EMA, PRICE_CLOSE, j + 1); // prior bar
         double s4 = iRSI(symbol, 0, 14, PRICE_CLOSE, j);

         double open   = iOpen(symbol, 0, j);
         double close  = iClose(symbol, 0, j);
         double high   = iHigh(symbol, 0, j);
         double low    = iLow(symbol, 0, j);
         int volume    = (int)iVolume(symbol, 0, j);
         int time      = (int)iTime(symbol, 0, j);

        // === Send Candle Batch ===
string csv = SerializeCandles(symbol, 100);
string payload = "candles:" + SerializeCandles(symbol, 100);
uchar sendBuf[4096];
StringToCharArray(payload, sendBuf);
uchar recvBuf[4096];
SendCandleBatch(sendBuf, ArraySize(sendBuf), recvBuf, ArraySize(recvBuf));


         
         // Optional: Log or batch
         string logLine = StringFormat("📈 %s Candle[%d]: s1=%.2f s2=%.2f s3=%.2f s4=%.2f Close=%.5f",
                                       symbol, j, s1, s2, s3, s4, close);
         //Print(logLine);
      }}

   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
   ObjectDelete(0, "PredictorInfo");
   Print("🛑 PredictorEA deinitialized.");
}

//+------------------------------------------------------------------+
void OnTick() {
   if (TradingPaused) {
      Comment("⏸️ Trading is paused.");
      return;
   }

   ManageOpenOrders();

   string symbols[];
   int symbolCount = StringSplit(TradeSymbols, ',', symbols);
   int candleLimit = 100;  // You can adjust this to fetch more/less candles

   for (int i = 0; i < symbolCount; i++) {
      string symbol = StringTrim(symbols[i]);
      if (symbol == "") continue;


   
      // === Handle the latest prediction (index 0 candle) ===
      double s1 = iRSI(symbol, 0, 14, PRICE_CLOSE, 0);
      double s2 = iMA(symbol, 0, 12, 0, MODE_EMA, PRICE_CLOSE, 0);
      double s3 = iMA(symbol, 0, 26, 0, MODE_EMA, PRICE_CLOSE, 1);
      double s4 = iRSI(symbol, 0, 14, PRICE_CLOSE, 0);

      double open = iOpen(symbol, 0, 0);
      double close = iClose(symbol, 0, 0);
      double high = iHigh(symbol, 0, 0);
      double low = iLow(symbol, 0, 0);
      int volume = (int)iVolume(symbol, 0, 0);
      int time = (int)iTime(symbol, 0, 0);

      char symbolArr[32];
      StringToCharArray(symbol, symbolArr);
SendIndicatorSignal(s1, s2, s3, s4, symbolArr, time, open, close, high, low, volume, buffer, ArraySize(buffer));


      string response = StringSubstr(CharArrayToString(buffer), 0, StringFind(CharArrayToString(buffer), ","));
      double confidence = StringToDouble(StringSubstr(CharArrayToString(buffer), StringFind(CharArrayToString(buffer), ",") + 1));

      Print("🔮 ", symbol, " → Prediction: ", response, " | Confidence: ", confidence);
      
      string arrowName = "PredictArrow_" + symbol + "_" + TimeToString(TimeCurrent(), TIME_SECONDS);
color arrowColor = (response == "up") ? clrLime : (response == "down") ? clrRed : clrYellow;
int arrowCode = (response == "up") ? 233 : (response == "down") ? 234 : 251;

double arrowPrice = (response == "up") ? low : (response == "down") ? high : close;

ObjectCreate(0, arrowName, OBJ_ARROW, 0, TimeCurrent(), arrowPrice);
ObjectSetInteger(0, arrowName, OBJPROP_ARROWCODE, arrowCode);
ObjectSetInteger(0, arrowName, OBJPROP_COLOR, arrowColor);
ObjectSetInteger(0, arrowName, OBJPROP_WIDTH, 2);

// Optional label
string labelName = arrowName + "_text";
ObjectCreate(0, labelName, OBJ_TEXT, 0, TimeCurrent(), arrowPrice);
ObjectSetInteger(0, labelName, OBJPROP_COLOR, arrowColor);
ObjectSetInteger(0, labelName, OBJPROP_FONTSIZE, 10);
ObjectSetString(0, labelName, OBJPROP_TEXT, StringFormat("📈 %s (%.2f)", response, confidence));


      // Get command from server
      uchar commandBuffer[128];
      GetCommand(commandBuffer, sizeof(commandBuffer));
      
      printf(CharArrayToString(commandBuffer));
      
      HandleCommand(commandBuffer);

      lastSymbol = symbol;
      lastSignal = response;
      lastConfidence = confidence;

      if (confidence < ConfidenceMin) continue;

      double ask = MarketInfo(symbol, MODE_ASK);
      double bid = MarketInfo(symbol, MODE_BID);
      int digits = (int)MarketInfo(symbol, MODE_DIGITS);
      double point = MarketInfo(symbol, MODE_POINT);

      double lot = CalculateLotSize(symbol, StopLossPips);
      double price = NormalizeDouble((response == "up") ? ask : bid, digits);
      double sl = NormalizeDouble((response == "up") ? price - StopLossPips * point : price + StopLossPips * point, digits);
      double tp = NormalizeDouble((response == "up") ? price + TakeProfitPips * point : price - TakeProfitPips * point, digits);

      int ticket = -1;
      if (response == "up") {
         ticket = OrderSend(symbol, OP_BUYLIMIT, lot, price, 3, sl, tp, "BuySignal", 0, 0, clrGreen);
      } else if (response == "down") {
         ticket = OrderSend(symbol, OP_SELLLIMIT, lot, price, 3, sl, tp, "SellSignal", 0, 0, clrRed);
      }

      if (ticket > 0) tradeCount++;
      else Print("❌ Order failed for ", symbol, ": ", GetLastError());
   }

   UpdateInfoBox();
}



void HandleCommand(const uchar &xbuffer[]) {
   string response = CharArrayToString(xbuffer);
   if (StringFind(response, ":") == -1) return;

   string command = StringTrim(StringSubstr(response, 0, StringFind(response, ":")));
   string payload = StringTrim(StringSubstr(response, StringFind(response, ":") + 1));

   string parts[];
   int count = StringSplit(payload, ',', parts);
   string symbol = count > 0 ? StringTrim(parts[0]) : Symbol();
   int digits = (int)MarketInfo(symbol, MODE_DIGITS);
   double point = MarketInfo(symbol, MODE_POINT);

   if (command == "log") {
      Print("📝 Server Log: ", payload);
   } else if (command == "alert") {
      Alert("📣 SERVER ALERT: ", payload);
   } else if (command == "pause") {
      TradingPaused = true;
      Print("⏸️ Trading paused by server.");
   } else if (command == "resume") {
      TradingPaused = false;
      Print("▶️ Trading resumed.");
   } else if (command == "shutdown") {
      ExpertRemove();
      Alert("🛑 Trading stopped by server.");
   }

   // === Market Buy ===
   else if (command == "buy") {
      double lot = count > 1 ? StringToDouble(parts[1]) : 0.1;
      double ask = MarketInfo(symbol, MODE_ASK);
      double sl = NormalizeDouble(ask - StopLossPips * point, digits);
      double tp = NormalizeDouble(ask + TakeProfitPips * point, digits);
      int ticket = OrderSend(symbol, OP_BUY, NormalizeDouble(lot, 2), ask, 3, sl, tp, "CommandBuy", 0, 0, clrGreen);
      if (ticket > 0) Print("✅ BUY order sent for ", symbol);
      else Print("❌ BUY order failed: ", GetLastError());
   }

   // === Market Sell ===
   else if (command == "sell") {
      double lot = count > 1 ? StringToDouble(parts[1]) : 0.1;
      double bid = MarketInfo(symbol, MODE_BID);
      double sl = NormalizeDouble(bid + StopLossPips * point, digits);
      double tp = NormalizeDouble(bid - TakeProfitPips * point, digits);
      int ticket = OrderSend(symbol, OP_SELL, NormalizeDouble(lot, 2), bid, 3, sl, tp, "CommandSell", 0, 0, clrRed);
      if (ticket > 0) Print("✅ SELL order sent for ", symbol);
      else Print("❌ SELL order failed: ", GetLastError());
   }

   // === Close All Orders for Symbol ===
   else if (command == "close") {
      for (int i = OrdersTotal() - 1; i >= 0; i--) {
         if (OrderSelect(i, SELECT_BY_POS, MODE_TRADES) && OrderSymbol() == symbol) {
            double price = (OrderType() == OP_BUY) ? MarketInfo(symbol, MODE_BID) : MarketInfo(symbol, MODE_ASK);
            bool closed = OrderClose(OrderTicket(), OrderLots(), price, 3, clrYellow);
            if (closed) Print("✅ Closed ", symbol, " ticket: ", OrderTicket());
            else Print("❌ Close failed: ", GetLastError());
         }
      }
   }

   // === Close All Orders (All Symbols) ===
   else if (command == "closeall") {
      for (int i = OrdersTotal() - 1; i >= 0; i--) {
         if (OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) {
            string sym = OrderSymbol();
            double price = (OrderType() == OP_BUY) ? MarketInfo(sym, MODE_BID) : MarketInfo(sym, MODE_ASK);
            bool closed = OrderClose(OrderTicket(), OrderLots(), price, 3, clrOrange);
            if (closed) Print("✅ Closed ", sym, " ticket: ", OrderTicket());
            else Print("❌ Close failed: ", GetLastError());
         }
      }
   }

   // === Modify SL/TP for Symbol Orders ===
   else if (command == "modify") {
      if (count < 3) {
         Print("⚠️ Modify command needs SYMBOL,SL,TP");
         return;
      }

      double newSL = NormalizeDouble(StringToDouble(parts[1]), digits);
      double newTP = NormalizeDouble(StringToDouble(parts[2]), digits);

      for (int i = OrdersTotal() - 1; i >= 0; i--) {
         if (OrderSelect(i, SELECT_BY_POS, MODE_TRADES) && OrderSymbol() == symbol) {
            bool modified = OrderModify(OrderTicket(), OrderOpenPrice(), newSL, newTP, 0, clrBlue);
            if (modified) Print("✅ Modified SL/TP for ", symbol, " → ", newSL, " / ", newTP);
            else Print("❌ Modify failed: ", GetLastError());
         }
      }
   }

   else {
      Print("⚠️ Unknown command: ", command);
   }
}

void ManageOpenOrders() {
   datetime now = TimeCurrent();

   for (int i = OrdersTotal() - 1; i >= 0; i--) {
      if (!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if (OrderSymbol() == "" || OrderType() > OP_SELL) continue;

      string sym = OrderSymbol();
      int type = OrderType();
      double entry = OrderOpenPrice();
      double lots = OrderLots();
      datetime openTime = OrderOpenTime();

      string res = CharArrayToString(buffer);

      string prediction = StringTrim(StringSubstr(res, 0, StringFind(res, ",")));
      double confidence = StringToDouble(StringSubstr(res, StringFind(res, ",") + 1));

      double currentPrice = (type == OP_BUY) ? MarketInfo(sym, MODE_BID) : MarketInfo(sym, MODE_ASK);
      double profitPoints = (type == OP_BUY) ? (currentPrice - entry) : (entry - currentPrice);
      double profitPercent = (profitPoints / entry) * 100.0;

      bool closeByReversal = (confidence >= ConfidenceMin) &&
                             ((type == OP_BUY && prediction == "down") ||
                              (type == OP_SELL && prediction == "up"));
      bool closeByProfit = profitPercent >= ProfitTargetPercent;
      bool closeByTimeout = (now - openTime) >= MaxTradeMinutes * 60;

      if (closeByReversal || closeByProfit || closeByTimeout) {
         double price = MarketInfo(sym, (type == OP_BUY) ? MODE_BID : MODE_ASK);
         bool closed = OrderClose(OrderTicket(), lots, price, 3, clrYellow);
         if (closed)
            Print("✅ Closed ", sym, " - Reason: ", 
                  closeByReversal ? "Reversal" : closeByProfit ? "Profit Target" : "Timeout");
         else
            Print("❌ Close failed for ", sym, " - Error: ", GetLastError());
      }
   }}
//+------------------------------------------------------------------+
double CalculateLotSize(string symbol, double stopLossPips) {
   double tickValue = MarketInfo(symbol, MODE_TICKVALUE);
   double risk = AccountFreeMargin() * RiskPercent / 100.0;
   double lotSize = risk / (stopLossPips * tickValue);
   return NormalizeDouble(lotSize, 2);
}

//+------------------------------------------------------------------+
void CreateInfoBox() {
   ObjectCreate(0, "PredictorInfo", OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, "PredictorInfo", OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, "PredictorInfo", OBJPROP_XDISTANCE, 10);
   ObjectSetInteger(0, "PredictorInfo", OBJPROP_YDISTANCE, 20);
   ObjectSetInteger(0, "PredictorInfo", OBJPROP_FONTSIZE, 12);
   ObjectSetInteger(0, "PredictorInfo", OBJPROP_COLOR, clrLime);
   ObjectSetInteger(0, "PredictorInfo", OBJPROP_BACK, true);
}

void UpdateInfoBox() {
   string info = "📊 PredictorEA Info\n" +
                 "Trades: " + IntegerToString(tradeCount) + "\n" +
                 "Profit: $" + DoubleToString(AccountProfit(), 2) + "\n" +
                 "Last: " + lastSymbol + " " + lastSignal + " (" + DoubleToString(lastConfidence, 5) + ")";
   ObjectSetString(0, "PredictorInfo", OBJPROP_TEXT, info);
}
