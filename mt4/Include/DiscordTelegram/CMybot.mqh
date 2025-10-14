
   #define CAPTION_COLOR   clrYellow
   #define LOSS_COLOR      clrOrangeRed
   #include <stdlib.mqh>
   #include <stderror.mqh>
   #include <DiscordTelegram\Comment.mqh>
   #include <DiscordTelegram\Telegram.mqh>

#include <DiscordTelegram\CMybot.mqh>

   const ENUM_TIMEFRAMES _periods[] = {PERIOD_M1,PERIOD_M5,PERIOD_M15,PERIOD_M30,PERIOD_H1,PERIOD_H4,PERIOD_D1,PERIOD_W1,PERIOD_MN1};
input ENUM_LANGUAGES InpLanguage;

string symbols[];

  
   enum EXECUTION_MODE{MARKET_ORDERS,LIMIT_ORDERS,STOPLOSS_ORDERS};
     

 //+------------------------------------------------------------------+
   //|   CMyBot                                                         |
   //+------------------------------------------------------------------+
   class CMyBot: public CCustomBot
   {
   private:
      ENUM_LANGUAGES    m_lang;
      string            m_symbol;
      ENUM_TIMEFRAMES   m_period;
      string            m_template;
      CArrayString      m_templates;
   
   public:
      //+------------------------------------------------------------------+
      void              Language(const ENUM_LANGUAGES _lang)
      {
         m_lang=_lang;
      }
   
      //+------------------------------------------------------------------+
         void myAlert(string sym,string type, string message)
     {
      if(type == "print")
         Print(message);
      else if(type == "error")
        {
         Print(type+" | @  "+sym+","+IntegerToString(Period())+" | "+message);
         SendMessage(channel,type+" | @  "+sym+","+IntegerToString(Period())+" | "+message);
        }
      else if(type == "order")
        {
        }
      else if(type == "modify")
        {
        }
     }
   
   int myOrderSend(string sym,int type, double price, double volume, string ordername ) //send order, return ticket ("price" is irrelevant for market orders)
     {
     
     string chatId =channel;
      if(!IsTradeAllowed()) return(-1);
      int ticket = -1;
      int retries = 0;
      int err = 0;
      int long_trades = TradesCount(OP_BUY);
      int short_trades = TradesCount(OP_SELL);
      int long_pending = TradesCount(OP_BUYLIMIT) + TradesCount(OP_BUYSTOP);
      int short_pending = TradesCount(OP_SELLLIMIT) + TradesCount(OP_SELLSTOP);
      string ordername_ = ordername;
      if(ordername != "")
         ordername_ = "("+ordername+")";
      //test Hedging
      if(!Hedging && ((type % 2 == 0 && short_trades + short_pending > 0) || (type % 2 == 1 && long_trades + long_pending > 0)))
        {
         myAlert(sym,"print", "Order"+ordername_+" not sent, hedging not allowed");
         
         SendMessage(channel,"Order"+ordername_+ "not sent, hedging not allowed");
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
         myAlert(sym,"print", "Order"+ordername_+" not sent, maximum reached");
        SendMessage(chatId, "Order"+ordername_+" not sent, maximum reached");
         return(-1);
        }
       double SL=0,TP=0;
      //prepare to send order
      while(IsTradeContextBusy()) Sleep(100);
      
     
      
      RefreshRates();
      if(type == OP_BUY || type==OP_BUYLIMIT || type==OP_BUYSTOP)
       {  price = MarketInfo(sym,MODE_ASK);
        SL= price -stoploss*MarketInfo(sym,MODE_POINT);
            
         TP= price +takeprofit*MarketInfo(sym,MODE_POINT);
         
        } 
      else if(type == OP_SELL || type==OP_SELLLIMIT || type==OP_SELLSTOP)
         {price =  price = MarketInfo(sym,MODE_BID);
         
         SL= price +stoploss*MarketInfo(sym,MODE_POINT);
            
         TP= price -takeprofit*MarketInfo(sym,MODE_POINT);
         
         
         }
      else if(price < 0) //invalid price for pending order
        {
        // myAlert(sym,"order", "Order"+ordername_+" not sent, invalid price for pending order");
         SendMessage(channel,"Order"+ordername_+" not sent, invalid price for pending order");
   	  return(-1);
        }
      int clr = (type % 2 == 1) ? clrWhite : clrGold;
      while(ticket < 0 && retries < OrderRetry)
        {
        LotDigits=(int)MarketInfo(sym,MODE_LOTSIZE);
        
         ticket = OrderSend(sym, type,
          NormalizeDouble(volume, LotDigits),
          NormalizeDouble(price,  (int)MarketInfo(sym,MODE_DIGITS))
           ,
           
          0, 
          SL, TP,
           ordername, 
           2234,
            0, clr);
         if(ticket < 0)
           {
            err = GetLastError();
            myAlert(sym,"print", "OrderSend"+ordername_+" error #"+IntegerToString(err)+" "+ErrorDescription(err));
            SendMessage(channel, "OrderSend"+ordername_+" failed "+IntegerToString(OrderRetry+1)+" times; error #"+IntegerToString(err)+" "+ErrorDescription(err));
   
                Sleep(OrderWait*1000);
           }
           
//       
//       if(ticket < 0)
//        {
//           myAlert(sym,"error", "OrderSend"+ordername_+" failed "+IntegerToString(OrderRetry+1)+" times; error #"+IntegerToString(err)+" "+ErrorDescription(err));
//           SendMessage(channel, "OrderSend"+ordername_+" failed "+IntegerToString(OrderRetry+1)+" times; error #"+IntegerToString(err)+" "+ErrorDescription(err));
//   
//         return(-1);
//        }
      string typestr[6] = {"Buy", "Sell", "Buy Limit", "Sell Limit", "Buy Stop", "Sell Stop"};
    
          myAlert(sym,"order", "Order sent"+ordername_+": "+typestr[type]+" "+sym+" Magic #"+IntegerToString(MagicNumber));
         SendMessage(channel,"Order sent"+ordername_+": "+typestr[type]+sym+" "+ (string)MagicNumber+" "+IntegerToString(MagicNumber));

         retries++;
        }
        return ticket;
     
   }
      int               Templates(const string _list)
      {
         m_templates.Clear();
         //--- parsing
         string text=StringTrim(_list);
         if(text=="")
            return(0);
   
         //---
         while(StringReplace(text,"  "," ")>0);
         StringReplace(text,";"," ");
         StringReplace(text,","," ");
   
         //---
         string array[];
         int amount=StringSplit(text,' ',array);
         amount=fmin(amount,5);
   
         for(int i=0; i<amount; i++)
         {
            array[i]=StringTrim(array[i]);
            if(array[i]!="")
               m_templates.Add(array[i]);
         }
   
         return(amount);
      }
   
      //+------------------------------------------------------------------+
      int               SendScreenShot(const long _chat_id,
                                       const string _symbol,
                                       const ENUM_TIMEFRAMES _period,
                                       const string _template=NULL)
      {
         int result=0;
   
         long chart_id=ChartOpen(_symbol,_period);
         if(chart_id==0)
            return(ERR_CHART_NOT_FOUND);
   
         ChartSetInteger(ChartID(),CHART_BRING_TO_TOP,true);
   
         //--- updates chart
         int wait=60;
         while(--wait>0)
         {
            if(SeriesInfoInteger(_symbol,_period,SERIES_SYNCHRONIZED))
               break;
            Sleep(500);
         }
   
         if(_template!=NULL)
            if(!ChartApplyTemplate(chart_id,_template))
               PrintError(_LastError,InpLanguage);
   
         ChartRedraw(chart_id);
         Sleep(500);
   
         ChartSetInteger(chart_id,CHART_SHOW_GRID,false);
   
         ChartSetInteger(chart_id,CHART_SHOW_PERIOD_SEP,false);
   
         string filename=StringFormat("%s%d.gif",_symbol,_period);
   
         if(FileIsExist(filename))
            FileDelete(filename);
         ChartRedraw(chart_id);
   
         Sleep(100);
   
         if(ChartScreenShot(chart_id,filename,800,600,ALIGN_RIGHT))
         {
            
            Sleep(100);
            
            //--- Need for MT4 on weekends !!!
            ChartRedraw(chart_id);
            
            SendChatAction(_chat_id,ACTION_UPLOAD_PHOTO);
   
            //--- waitng 30 sec for save screenshot
            wait=60;
            while(!FileIsExist(filename) && --wait>0)
               Sleep(500);
   
            //---
            if(FileIsExist(filename))
            {
               string screen_id;
               result=SendPhoto(screen_id,_chat_id,filename,_symbol+"_"+StringSubstr(EnumToString(_period),7));
            }
            else
            {
               string mask=m_lang==LANGUAGE_EN?"Screenshot file '%s' not created.":"Файл скриншота '%s' не создан.";
               PrintFormat(mask,filename);
            }
         }
   
         ChartClose(chart_id);
         return(result);
      }
   
   
   
   
   
   
   
   
     //+------------------------------------------------------------------+
      void              ProcessMessages(void)
      {
   
   #define EMOJI_TOP    "\xF51D"
   #define EMOJI_BACK   "\xF519"
   #define KEYB_MAIN    (m_lang==LANGUAGE_EN)?"[[\"Account Info\"],[\"Quotes\"],[\"Charts\"],[\"trade\"],[\"analysis\"],[\"report\"]]":"[[\"??????????\"],[\"?????????\"],[\"???????\"]]"
   #define KEYB_SYMBOLS "[[\""+EMOJI_TOP+"\",\"GBPUSD\",\"EURUSD\"],[\"AUDUSD\",\"USDJPY\",\"EURJPY\"],[\"USDCAD\",\"USDCHF\",\"EURCHF\"],[\"EURCAD\"],[\"USDCHF\"],[\"USDDKK\"],[\"USDJPY\"],[\"AUDCAD\"]]"
   #define KEYB_PERIODS "[[\""+EMOJI_TOP+"\",\"M1\",\"M5\",\"M15\"],[\""+EMOJI_BACK+"\",\"M30\",\"H1\",\"H4\"],[\" \",\"D1\",\"W1\",\"MN1\"]]"
   #define  TRADE_SYMBOLS "[[\""+EMOJI_TOP+"\",\"BUY\",\"SELL\",\"BUYLIMIT\"],[\""+EMOJI_BACK+"\",\"SELLLIMIT\",\"BUYSTOP\",\"SELLSTOP\"]]"
         for(int i=0; i<m_chats.Total(); i++)
      
         {
            CCustomChat *chat=m_chats.GetNodeAtIndex(i);
            if(!chat.m_new_one.done)
            {
               chat.m_new_one.done=true;
               string text=chat.m_new_one.message_text;
   
               //--- start
               if(StringFind(text,"start")>=0 || StringFind(text,"help")>=0)
               {
                  chat.m_state=0;
                  string msg="The bot works with your trading account:\n";
                  msg+="/info - get account information\n";
                  msg+="/quotes - get quotes\n";
                  msg+="/charts - get chart images\n";
                  msg+="/trade- start live  trade"; 
                 
                  msg+="/account -- get account infos ";
                  msg+="/analysis  -- get market analysis";
   
                  if(m_lang==LANGUAGE_RU)
                  {
                     msg="??? ???????? ? ????? ???????? ??????:\n";
                     msg+="/info - ????????? ?????????? ?? ?????\n";
                     msg+="/quotes - ????????? ?????????\n";
                     msg+="/charts - ????????? ??????\n";
                     msg+="/trade"; 
                    
                     msg+="/analysis";
                  }
   
                  SendMessage(chat.m_id,msg,ReplyKeyboardMarkup(KEYB_MAIN,false,false));
                  continue;
               }
   
               //---
               if(text==EMOJI_TOP)
               {
                  chat.m_state=0;
                  string msg=(m_lang==LANGUAGE_EN)?"Choose a menu item":"???????? ????? ????";
                  SendMessage(chat.m_id,msg,ReplyKeyboardMarkup(KEYB_MAIN,false,false));
                  continue;
               }
   
               //---
               if(text==EMOJI_BACK)
               {
                  if(chat.m_state==31)
                  {
                     chat.m_state=3;
                     string msg=(m_lang==LANGUAGE_EN)?"Enter a symbol name like 'EURUSD'":"??????? ???????? ???????????, ???????? 'EURUSD'";
                     SendMessage(chat.m_id,msg,ReplyKeyboardMarkup(KEYB_SYMBOLS,false,false));
                  }
                  else if(chat.m_state==32)
                  {
                     chat.m_state=31;
                     string msg=(m_lang==LANGUAGE_EN)?"Select a timeframe like 'H1'":"??????? ?????? ???????, ???????? 'H1'";
                     SendMessage(chat.m_id,msg,ReplyKeyboardMarkup(KEYB_PERIODS,false,false));
                  }
                  else
                  {
                     chat.m_state=0;
                     string msg=(m_lang==LANGUAGE_EN)?"Choose a menu item":"???????? ????? ????";
                     SendMessage(chat.m_id,msg,ReplyKeyboardMarkup(KEYB_MAIN,false,false));
                  }
                  continue;
               }
   
               //---
               if(text=="/info" || text=="Account Info" || text=="??????????")
               {
                  chat.m_state=1;
                  string currency=AccountInfoString(ACCOUNT_CURRENCY);
                  string msg=StringFormat("%d: %s\n",AccountInfoInteger(ACCOUNT_LOGIN),AccountInfoString(ACCOUNT_SERVER));
                  msg+=StringFormat("%s: %.2f %s\n",(m_lang==LANGUAGE_EN)?"Balance":"??????",AccountInfoDouble(ACCOUNT_BALANCE),currency);
                  msg+=StringFormat("%s: %.2f %s\n",(m_lang==LANGUAGE_EN)?"Profit":"???????",AccountInfoDouble(ACCOUNT_PROFIT),currency);
                  SendMessage(chat.m_id,msg,ReplyKeyboardMarkup(KEYB_MAIN,false,false));
                  continue;
               }
   
               //---
               if(text=="/quotes" || text=="Quotes" || text=="?????????")
               {
                  chat.m_state=2;
                  string msg=(m_lang==LANGUAGE_EN)?"Enter a symbol name like 'EURUSD'":"??????? ???????? ???????????, ???????? 'EURUSD'";
                  SendMessage(chat.m_id,msg,ReplyKeyboardMarkup(KEYB_SYMBOLS,false,false));
                  continue;
               }
   
               //---
               if(text=="/charts" || text=="Charts" || text=="chart"|| text=="???????")
               {
                  chat.m_state=3;
                  string msg=(m_lang==LANGUAGE_EN)?"Enter a symbol name like 'EURUSD'":"??????? ???????? ???????????, ???????? 'EURUSD'";
                  SendMessage(chat.m_id,msg,ReplyKeyboardMarkup(KEYB_SYMBOLS,false,false));
                  continue;
               }
               //Trade 
               
               
               
               if(text== "/trade" || text=="trade"){
               
               string msg="=======TRADE MODE====== \nSelect symbol!";
                SendMessage(chat.m_id,msg,ReplyKeyboardMarkup(KEYB_SYMBOLS,false,false));
               chat.m_state =4;
              
              }
              if(text=="/analysis"|| text=="analysis"){
              
                string msg="=========== Market Analysis ==========";
               SendMessage(chat.m_id,msg,ReplyKeyboardMarkup(TRADE_SYMBOLS,false,false));
               chat.m_state=7;
              
              }
             if(text=="/report"||text=="report"){
               string msg="========Trade Report ======";
               msg=StringFormat("Date %s\nBalance %s\nEquity %s\nProfit %s\nDaily Losses %s\nExpected Return :%s\n Weekly Report%s\n",
               TimeToStr(TimeCurrent()), DoubleToStr(AccountBalance()),
               DoubleToStr(AccountEquity()), DoubleToStr(-AccountBalance()+AccountEquity()),
              DoubleToStr( 1),DoubleToStr((AccountEquity()/AccountBalance())*100),
              
              ((SymbolName(i,false)==text)? text:Symbol()) +(string)(0)+ " pips"
               
               );
              
                SendMessage(chat.m_id,msg,ReplyKeyboardMarkup(KEYB_MAIN,false,false));
              
                chat.m_state=6;
              }
     


              
   int ticket=0;
   string symbol="";
        //CREATE ORDERS
        
              ObjectCreate(ChartID(),"symb", OBJ_LABEL,0,Time[0],MarketInfo(      Symbol(),MODE_ASK));
              
        //SEARCHING  SYMBOL TO CREATE ORDER
        int j=0;int immediateExecution = ImmediateExecution;
        while(j<SymbolsTotal(false)){
                 StringToUpper(text);
               switch (immediateExecution) {
    case MARKET_ORDERS:
        if (StringFind(text, SymbolName(j, false), 0) >= 0) {
            string symb = SymbolName(j, false);
            ObjectSetInteger(ChartID(), "symb", OBJPROP_YDISTANCE, 200);
            ObjectSetInteger(ChartID(), "symb", OBJPROP_XDISTANCE, 1);
            ObjectSetText("symb", "Telegram Symbol: " + symb, 13, NULL, clrYellow);

            if (StringFind(text, "SELL", 0) >= 0) {
                ticket = myOrderSend(symb, OP_SELL, MarketInfo(symb, MODE_BID), Lots, "MARKET SELL ORDER");
                if (ticket < 0) SendMessage(chat.m_id, " ERROR " + GetErrorDescription(GetLastError(), 0));
            } else if (StringFind(text, "BUY", 0) >= 0) {
                ticket = myOrderSend(symb, OP_BUY, MarketInfo(symb, MODE_ASK), Lots, "MARKET BUY ORDER");
                if (ticket < 0) SendMessage(chat.m_id, " ERROR " + GetErrorDescription(GetLastError(), 0));
            }
        }
        break;

    case LIMIT_ORDERS:
        if (StringFind(text, SymbolName(j, false), 0) >= 0) {
            string symb = SymbolName(j, false);
            ObjectSetInteger(ChartID(), "symb", OBJPROP_YDISTANCE, 200);
            ObjectSetInteger(ChartID(), "symb", OBJPROP_XDISTANCE, 1);
            ObjectSetText("symb", "Telegram Symbol: " + symb, 13, NULL, clrYellow);

            if (StringFind(text, "BUY", 0) >= 0) {
                ticket = myOrderSend(symb, OP_BUYLIMIT, MarketInfo(symb, MODE_ASK), Lots, "BUY LIMIT ORDER");
                if (ticket < 0) SendMessage(chat.m_id, " ERROR " + GetErrorDescription(GetLastError(), 0));
            } else if (StringFind(text, "SELL", 0) >= 0) {
                ticket = myOrderSend(symb, OP_SELLLIMIT, MarketInfo(symb, MODE_BID), Lots, "SELL Limit ORDER");
                if (ticket < 0) SendMessage(chat.m_id, " ERROR " + GetErrorDescription(GetLastError(), 0));
            }
        }
        break;

    case STOPLOSS_ORDERS:
        if (StringFind(text, SymbolName(j, false), 0) >= 0) {
            string symb = SymbolName(j, false);
            ObjectSetInteger(ChartID(), "symb", OBJPROP_YDISTANCE, 200);
            ObjectSetInteger(ChartID(), "symb", OBJPROP_XDISTANCE, 1);
            ObjectSetText("symb", "Telegram Symbol: " + symb, 13, NULL, clrYellow);

            if (StringFind(text, "BUY", 0) >= 0) {
                ticket = myOrderSend(symb, OP_BUYSTOP, MarketInfo(symb, MODE_ASK), Lots, "BUY STOPLOSS ORDER");
                if (ticket < 0) SendMessage(chat.m_id, " ERROR " + GetErrorDescription(GetLastError(), 0));
            } else if (StringFind(text, "SELL", 0) >= 0) {
                ticket = myOrderSend(symb, OP_SELLSTOP, MarketInfo(symb, MODE_BID), Lots, "SELL STOPLOSS ORDER");
                if (ticket < 0) SendMessage(chat.m_id, " ERROR " + GetErrorDescription(GetLastError(), 0));
            }
        }
        break;

    default:printf("NO ORDER SEND YET");
        // Handle default case if ImmediateExecution doesn't match any known value
        break;
}
                  j++;
                  
                 }
    
               //--- Quotes
               if(chat.m_state==2)
               {
                  string mask=(m_lang==LANGUAGE_EN)?"  Invalid symbol name '%s'":"?????????? '%s' ?? ??????";
                  string msg=StringFormat(mask,text);
                  StringToUpper(text);
                  symbol=text;
                  if(SymbolSelect(symbol,true))
                  {
                     double open[1]= {0};
   
                     m_symbol=symbol;
                     //--- upload history
                     for(int k=0; k<3; k++)
                     {
   #ifdef __MQL4__
                        double array[][6];
                        ArrayCopyRates(array,symbol,PERIOD_D1);
   #endif
   
                        Sleep(2000);
                        CopyOpen(symbol,PERIOD_D1,0,1,open);
                        if(open[0]>0.0)
                           break;
                     }
   
                     int digits=(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS);
                     double bid=SymbolInfoDouble(symbol,SYMBOL_BID);
   
                     CopyOpen(symbol,PERIOD_D1,0,1,open);
                     if(open[0]>0.0)
                     {
                        double percent=100*(bid-open[0])/open[0];
                        //--- sign
                        string sign=ShortToString(0x25B2);
                        if(percent<0.0)
                           sign=ShortToString(0x25BC);
   
                        msg=StringFormat("%s: %s %s (%s%%)",symbol,DoubleToString(bid,digits),sign,DoubleToString(percent,2));
                     }
                     else
                     {
                        msg=(m_lang==LANGUAGE_EN)?"No history for ":"??? ??????? ??? "+symbol;
                     }
                  }
   
                  SendMessage(chat.m_id,msg,ReplyKeyboardMarkup(KEYB_SYMBOLS,false,false));
                  continue;
               }
     ArrayResize(symbols,SymbolsTotal(false),0);
               //--- Charts
               if(chat.m_state==3)
               {
   
                  StringToUpper(text);
                  symbol=text;
                  if(SymbolSelect(symbol,true))
                  {
                     m_symbol=symbol;
   
                     chat.m_state=31;
                     string msg=(m_lang==LANGUAGE_EN)?"Select a timeframe like 'H1'":"??????? ?????? ???????, ???????? 'H1'";
                     SendMessage(chat.m_id,msg,ReplyKeyboardMarkup(KEYB_PERIODS,false,false));
                  }
                  else
                  {
                     string mask=(m_lang==LANGUAGE_EN)?"Invalid symbol name '%s'":"?????????? '%s' ?? ??????";
                     string msg=StringFormat(mask,text);
                     SendMessage(chat.m_id,msg,ReplyKeyboardMarkup(KEYB_SYMBOLS,false,false));
                  }
                  continue;
               }
   
   
   
    if(i<SymbolsTotal(false)){
               
               
               
                for (j =0;j<SymbolsTotal(false);j++){
                  if(StringFind(text,SymbolName(j,false),0)>=0){
                  
                symbols[0]=SymbolName(j,false);
                          Comment(symbols[0]);
                break; 
                }
          
                }
             
             }
   
   
   
   
                printf("sym[0] :"+symbols[0]);
                if(StringFind(text,"BUY",0)>=0 )
                  {
                
               myOrderSend(symbols[0],OP_BUY,MarketInfo(symbols[0],MODE_ASK),Lots,"MARKET BUY  ORDER");
               
              
              }else
              
               if(StringFind(text,"SELL",0)>=0 ){
                    
               myOrderSend(symbols[0],OP_SELL,MarketInfo(symbols[0],MODE_BID),Lots,"MARKET SELL ORDER");
               
              
                 }
                 
                  // CREATE LIMIT ORDERS 
                    
              if(StringFind(text,"BUYLIMIT",0)>=0 ){                        
                  ticket =myOrderSend(symbols[0],OP_BUYLIMIT,MarketInfo(symbols[0],MODE_ASK),Lots,"BUY LIMIT ORDER");
              
              }
              else 
     
              if( StringFind(text,"SELLLIMIT",0)>=0 ){
                    
                ticket =myOrderSend(symbols[0],OP_SELLLIMIT,MarketInfo(symbols[0],MODE_BID),Lots,"SELL Limit ORDER");
                
              
              }  
      
             // CREATE STOPLOSS ORDER 
              if(StringFind(text,"BUYSTOP",0)>=0 ){                              
               ticket =myOrderSend(symbols[0],OP_BUYSTOP,MarketInfo(symbols[0],MODE_ASK),Lots,"BUY STOPLOSS ORDER");

              }else
              
               if(StringFind(text,"SELLSTOP",0)>=0 ){
                 ticket =myOrderSend(symbols[0],OP_SELLSTOP,MarketInfo(symbols[0],MODE_BID),Lots,"SELL STOPLOSS ORDER");
                      }
   
   
           
        if(chat.m_state ==4){
                
             if(i<SymbolsTotal(false)){
          
                for (j =0;j<SymbolsTotal(false);j++){
                  if(StringFind(text,SymbolName(j,false),0)>=0){
                  
                symbols[0]=SymbolName(j,false);
                      SendMessage(chat.m_id,"Click buttons to trade",ReplyKeyboardMarkup(TRADE_SYMBOLS,false,false));
                    chat.m_state=5;
                    Comment(symbols[0]);
                break;  }
          
                }
             
             }
         }
          
          
             
          while(chat.m_state==5){//trade state
          
   
                printf("sym[0] :"+symbols[0]);
                if(StringFind(text,"BUY",0)>=0 )
                  {
                
               myOrderSend(symbols[0],OP_BUY,MarketInfo(symbols[0],MODE_ASK),Lots,"MARKET BUY  ORDER");
               
              
              }else
              
               if(StringFind(text,"SELL",0)>=0 ){
                    
               myOrderSend(symbols[0],OP_SELL,MarketInfo(symbols[0],MODE_BID),Lots,"MARKET SELL ORDER");
               
              
                 }
                 
                  // CREATE LIMIT ORDERS 
                    
              if(StringFind(text,"BUYLIMIT",0)>=0 || StringFind(text,"BUY_LIMIT",0)>=0 ){                        
                 myOrderSend(symbols[0],OP_BUYLIMIT,MarketInfo(symbols[0],MODE_ASK),Lots,"BUY LIMIT ORDER");
              
              }
              else 
     
              if( StringFind(text,"SELLLIMIT",0)>=0||StringFind(text,"SELL_LIMIT",0)>=0 ){
                    
                ticket =myOrderSend(symbols[0],OP_SELLLIMIT,MarketInfo(symbols[0],MODE_BID),Lots,"SELL Limit ORDER");
                
              
              }  
      
             // CREATE STOPLOSS ORDER 
              if(StringFind(text,"BUYSTOP",0)>=0|| StringFind(text,"BUY_STOP",0)>=0 ){                              
               ticket =myOrderSend(symbols[0],OP_BUYSTOP,MarketInfo(symbols[0],MODE_ASK),Lots,"BUY STOPLOSS ORDER");

              }else
              
               if(StringFind(text,"SELLSTOP",0)>=0||StringFind(text,"SELL_STOP",0)>=0 ){
                 ticket =myOrderSend(symbols[0],OP_SELLSTOP,MarketInfo(symbols[0],MODE_BID),Lots,"SELL STOPLOSS ORDER");
                      }
              break;            
        }
             //Charts->Periods
               if(chat.m_state==31)
               {
                  bool found=false;
                  int total=ArraySize(_periods);
                  for(int k=0; k<total; k++)
                  {
                     string str_tf=StringSubstr(EnumToString(_periods[k]),7);
                     if(StringCompare(str_tf,text,false)==0)
                     {
                        m_period=_periods[k];
                        found=true;
                        break;
                     }
                  }
   
                  if(found)
                  {
                     //--- template
                     chat.m_state=32;
                     string str="[[\""+EMOJI_BACK+"\",\""+EMOJI_TOP+"\"]";
                     str+=",[\"None\"]";
                     for(int k=0; k<m_templates.Total(); k++)
                        str+=",[\""+m_templates.At(k)+"\"]";
                     str+="]";
   
                     SendMessage(chat.m_id,(m_lang==LANGUAGE_EN)?"Select a template":"???????? ??????",ReplyKeyboardMarkup(str,false,false));
                  }
                  else
                  {
                     SendMessage(chat.m_id,(m_lang==LANGUAGE_EN)?"Invalid timeframe":"??????????? ????? ?????? ???????",ReplyKeyboardMarkup(KEYB_PERIODS,false,false));
                  }
                  continue;
               }
               //---
               if(chat.m_state==32)
               {
                  m_template=text;
                  if(m_template=="None")
                     m_template=NULL;
                  int result=SendScreenShot(chat.m_id,m_symbol,m_period,m_template);
                  if(result!=0)
                     Print(GetErrorDescription(result,InpLanguage));
               }
            }
         }
      }
   
   
   
   
   
   
   
   
      //+------------------------------------------------------------------+
     };

  
//+------------------------------------------------------------------+

enum MONEY_MANAGEMENT
  {
   RISK_PERCENTAGE,
   POSITION_SIZE,
   MARTINGALE,
   FIXED_SIZE
  }
;



enum Answer {yes, no};


enum DYS_WEEK
  {
   Sunday = 0,
   Monday = 1,
   Tuesday = 2,
   Wednesday,
   Thursday = 4,
   Friday = 5,
   Saturday
  };

enum TIME_LOCK
  {
   closeall,//CLOSE_ALL_TRADES
   closeprofit,//CLOSE_ALL_PROFIT_TRADES
   breakevenprofit//MOVE_PROFIT_TRADES_TO_BREAKEVEN
  };





//---
CComment       comment;
CMyBot         bot;
ENUM_RUN_MODE  run_mode;
datetime       time_check;
int            web_error;
int            init_error;
string         photo_id = NULL;
int siz = 0;



int MagicNumber = 123;






//  Input parameters                                               |
input ENUM_UPDATE_MODE  InpUpdateMode = UPDATE_NORMAL; //Update Mode
input string            InpToken = "2032573404:AAGnxJpNMJBKqLzvE5q4kGt1cCGF632bP7A"; //Token
input long ChatID = -1001648392740; //CHAT OR GROUP ID

input string CHANNEL_NAME = "tradeexpert_infos";
long TELEGRAM_GROUP_CHAT_ID = ChatID;
string            InpUserNameFilter = ""; //Whitelist Usernames
input   string            InpTemplates = "ADX,RSI, ADX,Momentum"; //Templates for screenshot

//I need an expert to develop a Telegram to MT4 & MT5 copying system with the following functions:


input EXECUTION_MODE  ImmediateExecution;// TRADE MODE

input MONEY_MANAGEMENT  money_management;// MONEY MANAGEMENT
input bool  Move_SL_Automatically = true; // MOVE SL AUTOMATICALLY
input bool  Move_TP_to_Breakeven = true; //MOVE TP TO BREAKEVEN


input int slippage = 2; //SLIPPAGE
input int stoploss = 100; // SL IN POINT
input int takeprofit = 100; // SL IN POINT
extern string  h1                   = "===Time Management System==="; // =========Monday==========
input  Answer   SET_TRADING_DAYS     = no;
input  DYS_WEEK EA_START_DAY        = Sunday;//Starting Day
input string EA_START_TIME          = "22:00";
input DYS_WEEK EA_STOP_DAY          = Friday;//Ending Day
input string EA_STOP_TIME          = "22:00";


input string fsiz;//FIXED SIZE PARAMS
input double lotSize = 0.01; //FIXED SIZE

input string sddd; //MATINGALE PARAMS
input   double MM_Martingale_Start = 0.01;
input double MM_Martingale_ProfitFactor = 1;
input double MM_Martingale_LossFactor = 2;
input bool MM_Martingale_RestartProfit = true;
input bool MM_Martingale_RestartLoss = false;
input int MM_Martingale_RestartLosses = 1000;
input int MM_Martingale_RestartProfits = 1000;
input string psds;//POSITION SIZE PARAMS


input double MM_PositionSizing = 10000;








//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
double Position_Size(string sym) //position sizing
  {
   double MaxLot = MarketInfo(sym, MODE_MAXLOT);
   double MinLot = MarketInfo(sym, MODE_MINLOT);
   double lots = AccountBalance() / MM_PositionSizing;
   if(lots > MaxLot)
      lots = MaxLot;
   if(lots < MinLot)
      lots = MinLot;
   return(lots);
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
double MM_Size(string sym) //martingale / anti-martingale
  {
   double lots = MM_Martingale_Start;
   double MaxLot = MarketInfo(sym, MODE_MAXLOT);
   double MinLot = MarketInfo(sym, MODE_MINLOT);
   if(SelectLastHistoryTrade(sym))
     {
      double orderprofit = OrderProfit();
      double orderlots = OrderLots();
      double boprofit = BOProfit(OrderTicket());
      if(orderprofit + boprofit > 0 && !MM_Martingale_RestartProfit)
         lots = orderlots * MM_Martingale_ProfitFactor;
      else
         if(orderprofit + boprofit < 0 && !MM_Martingale_RestartLoss)
            lots = orderlots * MM_Martingale_LossFactor;
         else
            if(orderprofit + boprofit == 0)
               lots = orderlots;
     }
   if(ConsecutivePL(false, MM_Martingale_RestartLosses))
      lots = MM_Martingale_Start;
   if(ConsecutivePL(true, MM_Martingale_RestartProfits))
      lots = MM_Martingale_Start;
   if(lots > MaxLot)
      lots = MaxLot;
   if(lots < MinLot)
      lots = MinLot;
   return(lots);
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
bool SelectLastHistoryTrade(string sym)
  {
   int lastOrder = -1;
   int total = OrdersHistoryTotal();
   for(int i = total - 1; i >= 0; i--)
     {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_HISTORY))
         continue;
      if(OrderSymbol() == sym && OrderMagicNumber() == MagicNumber)
        {
         lastOrder = i;
         break;
        }
     }
   return(lastOrder >= 0);
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
double BOProfit(int ticket) //Binary Options profit
  {
   int total = OrdersHistoryTotal();
   for(int i = total - 1; i >= 0; i--)
     {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_HISTORY))
         continue;
      if(StringSubstr(OrderComment(), 0, 2) == "BO" && StringFind(OrderComment(), "#" + IntegerToString(ticket) + " ") >= 0)
         return OrderProfit();
     }
   return 0;
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
bool ConsecutivePL(bool profits, int n)
  {
   int count = 0;
   int total = OrdersHistoryTotal();
   for(int i = total - 1; i >= 0; i--)
     {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_HISTORY))
         continue;
      if(OrderSymbol() == Symbol() && OrderMagicNumber() == MagicNumber)
        {
         double orderprofit = OrderProfit();
         double boprofit = BOProfit(OrderTicket());
         if((!profits && orderprofit + boprofit >= 0) || (profits && orderprofit + boprofit <= 0))
            break;
         count++;
        }
     }
   return(count >= n);
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
double  GetLotSize(MONEY_MANAGEMENT money)
  {
string sym=Symbol();
   if(money == RISK_PERCENTAGE)
     {
      return MM_Size(sym);
     }
   else
      if(money == MARTINGALE)
        {
         return MM_Size(sym);
        }
      else
         if(money == POSITION_SIZE)
           {
            return Position_Size(sym);
           }
         else
            if(money == FIXED_SIZE)
               return lotSize;
   return 0.01;
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void CloseAll()
  {
   int totalOP  = OrdersTotal(), tiket = 0;
   for(int cnt = totalOP - 1 ; cnt >= 0 ; cnt--)
     {
      int Oc = 0, Os = OrderSelect(cnt, SELECT_BY_POS, MODE_TRADES);
      if(OrderType() == OP_BUY && OrderMagicNumber() == MagicNumber)
        {
         Oc = OrderClose(OrderTicket(), OrderLots(), MarketInfo(OrderSymbol(), MODE_BID), 3, CLR_NONE);
         Sleep(300);
         continue;
        }
      if(OrderType() == OP_SELL && OrderMagicNumber() == MagicNumber)
        {
         Oc = OrderClose(OrderTicket(), OrderLots(), MarketInfo(OrderSymbol(), MODE_ASK), 3, CLR_NONE);
         Sleep(300);
        }
     }
  }


//+------------------------------------------------------------------+
//|             TradeDays                                                     |
//+------------------------------------------------------------------+
bool TradeDays()
  {
   if(SET_TRADING_DAYS == no)
      return(true);
   bool ret = false;
   int today = DayOfWeek();
   if(EA_START_DAY < EA_STOP_DAY)
     {
      if(today > EA_START_DAY && today < EA_STOP_DAY)
         return(true);
      else
         if(today == EA_START_DAY)
           {
            if(TimeCurrent() >= datetime(StringToTime(EA_START_TIME)))
               return(true);
            else
               return(false);
           }
         else
            if(today == EA_STOP_DAY)
              {
               if(TimeCurrent() < datetime(StringToTime(EA_STOP_TIME)))
                  return(true);
               else
                  return(false);
              }
     }
   else
      if(EA_STOP_DAY < EA_START_DAY)
        {
         if(today > EA_START_DAY || today < EA_STOP_DAY)
            return(true);
         else
            if(today == EA_START_DAY)
              {
               if(TimeCurrent() >= datetime(StringToTime(EA_START_TIME)))
                  return(true);
               else
                  return(false);
              }
            else
               if(today == EA_STOP_DAY)
                 {
                  if(TimeCurrent() < datetime(StringToTime(EA_STOP_TIME)))
                     return(true);
                  else
                     return(false);
                 }
        }
      else
         if(EA_STOP_DAY == EA_START_DAY)
           {
            datetime st = (datetime)StringToTime(EA_START_TIME);
            datetime et = (datetime)StringToTime(EA_STOP_TIME);
            if(et > st)
              {
               if(today != EA_STOP_DAY)
                  return(false);
               else
                  if(TimeCurrent() >= st && TimeCurrent() < et)
                     return(true);
                  else
                     return(false);
              }
            else
              {
               if(today != EA_STOP_DAY)
                  return(true);
               else
                  if(TimeCurrent() >= et && TimeCurrent() < st)
                     return(false);
                  else
                     return(true);
              }
           }
   /*int JamH1[] = { 10, 20, 30, 40 }; // A[2] == 30
    //   if (JamH1[Hour()] == Hour()) Alert("Trade");
    if (Hour() >= StartHour1 && Hour() <= EndHour1 && DayOfWeek() == 1 && MondayTrade )  return (true);
    if (Hour() >= StartHour2 && Hour() <= EndHour2 && DayOfWeek() == 2 && TuesdayTrade )  return (true);
    if (Hour() >= StartHour3 && Hour() <= EndHour3 && DayOfWeek() == 3 && WednesdayTrade )  return (true);
    if (Hour() >= StartHour4 && Hour() <= EndHour4 && DayOfWeek() == 4 && ThursdayTrade )  return (true);
    if (Hour() >= StartHour5 && Hour() <= EndHour5 && DayOfWeek() == 5 && FridayTrade && !ExitFriday)  return (true);
    if (StartHour5 <=StartHourX - LastTradeFriday - 1 && Hour() >= StartHour5 && Hour() <= StartHourX - LastTradeFriday - 1 && DayOfWeek() == 5 && FridayTrade && ExitFriday)  return (true);
    if ( DayOfWeek() == 1 && !MondayTrade )  return (true);
    if ( DayOfWeek() == 2 && !TuesdayTrade )  return (true);
    if ( DayOfWeek() == 3 && !WednesdayTrade )  return (true);
    if ( DayOfWeek() == 4 && !ThursdayTrade )  return (true);
    if ( DayOfWeek() == 5 && !FridayTrade && ExitFridayOk() == 0)  return (true);
    */
   return (ret);
  }

////////////////////////////////////////////////////////////////////////
void timelockaction(void)
  {
   if(TradeDays())
      return;
   double stoplevel = 0, proffit = 0, newsl = 0, price = 0;
   double ask = 0, bid = 0;
   string sy = NULL;
   int sy_digits = 0;
   double sy_points = 0;
   bool ans = false;
   bool next = false;
   int otype = -1;
   int kk = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         continue;
      if(OrderMagicNumber() != MagicNumber)
         continue;
      next = false;
      ans = false;
      sy = OrderSymbol();
      ask = SymbolInfoDouble(sy, SYMBOL_ASK);
      bid = SymbolInfoDouble(sy, SYMBOL_BID);
      sy_digits = (int)SymbolInfoInteger(sy, SYMBOL_DIGITS);
      sy_points = SymbolInfoDouble(sy, SYMBOL_POINT);
      stoplevel = MarketInfo(sy, MODE_STOPLEVEL) * sy_points;
      otype = OrderType();
      kk = 0;
      proffit = OrderProfit() + OrderSwap() + OrderCommission();
      newsl = OrderOpenPrice();
      if(proffit <= 0)
         break;
      else
        {
         price = (otype == OP_BUY) ? bid : ask;
         while(otype < 2 && kk < 5 && MathAbs(price - newsl) >= stoplevel && !OrderModify(OrderTicket(), newsl, newsl, OrderTakeProfit(), OrderExpiration()))
           {
            kk++;
            price = (otype == OP_BUY) ? SymbolInfoDouble(sy, SYMBOL_BID) : SymbolInfoDouble(sy, SYMBOL_ASK);
           }
        }
      continue;
     }
  }

//+------------------------------------------------------------------+
//|                     CHART COLOR SET                                             |
//+------------------------------------------------------------------+
bool ChartColorSet()//set chart colors
  {
   ChartSetInteger(ChartID(), CHART_COLOR_ASK, BearCandle);
   ChartSetInteger(ChartID(), CHART_COLOR_BID, clrOrange);
   ChartSetInteger(ChartID(), CHART_COLOR_VOLUME, clrAqua);
   int keyboard = 12;
   ChartSetInteger(ChartID(), CHART_KEYBOARD_CONTROL, keyboard);
   ChartSetInteger(ChartID(), CHART_COLOR_CHART_DOWN, 231);
   ChartSetInteger(ChartID(), CHART_COLOR_CANDLE_BEAR, BearCandle);
   ChartSetInteger(ChartID(), CHART_COLOR_CANDLE_BULL, BullCandle);
   ChartSetInteger(ChartID(), CHART_COLOR_CHART_DOWN, Bear_Outline);
   ChartSetInteger(ChartID(), CHART_COLOR_CHART_UP, Bull_Outline);
   ChartSetInteger(ChartID(), CHART_SHOW_GRID, 0);
   ChartSetInteger(ChartID(), CHART_SHOW_PERIOD_SEP, false);
   ChartSetInteger(ChartID(), CHART_MODE, 1);
   ChartSetInteger(ChartID(), CHART_SHIFT, 1);
   ChartSetInteger(ChartID(), CHART_SHOW_ASK_LINE, 1);
   ChartSetInteger(ChartID(), CHART_COLOR_BACKGROUND, BackGround);
   ChartSetInteger(ChartID(), CHART_COLOR_FOREGROUND, ForeGround);
   return(true);
  }

input color BearCandle = clrWhite;
input color BullCandle = clrGreen;
input color BackGround = clrBlack;
input color ForeGround = clrAquamarine;
input color Bear_Outline = clrRed;
input color Bull_Outline = clrGreen;
input string license_key = "trial";
bool CheckLicense(string license)
  {
   datetime tim = D'2023.07.01 00:00';
   if(license == "trial")
     {
      int op = FileOpen(license, FILE_WRITE | FILE_CSV);
      if(op < 0)
        {
         printf("Can't open license key folder");
         return false;
        }
      uint write = FileWrite(op, license_key + (string)AccountNumber() + (string)TimeCurrent());
      FileClose(op);
      Comment("\n\n                                                     Trial Mode");
      if(tim > TimeCurrent())
        {
         return true;
        }
      else
        {
         MessageBox("Your trial Mode is Over!Please purchase a new license to get access to a full product.You can also contact support at https://t.me/tradeexpert_infos"
                    , NULL, 1);
         return false;
        }
     }
   else
     {
      return false;
     }
   return false;
  }

//+------------------------------------------------------------------+
//|   TRADE EXPERT parameters                                               |
//+------------------------------------------------------------------+

input string auth;//==========AUTH PARAMS ================
input ENUM_LICENSE_TYPE licenseType = 0;
input string LICENSE_KEY = "3EEEE4";
input string email = "test";
input string password = "12349";

input const string ss15 ;// "============== TELEGRAM BOT SETTINGS ================";


input string channel = "tradeexpert_infos"; // TELEGRAM CHANNEL
input long chatID = -1001648392740; // GROUP or BOT CHAT ID

input Answer telegram = yes;
input bool UseAllSymbol = true;
input bool trade0 = false;//Trade News
bool now = false;

//+------------------------------------------------------------------+
//|                         NEWS                                         |
//+------------------------------------------------------------------+
bool AvoidNews = trade0;

//-------------------------------------------- EXTERNAL VARIABLE ---------------------------------------------
//------------------------------------------------------------------------------------------------------------
extern bool    ReportActive      = true;                // Report for active chart only (override other inputs)
extern bool    IncludeHigh       = true;                 // Include high
extern bool    IncludeMedium     = true;                 // Include medium
extern bool    IncludeLow        = true;                 // Include low
extern bool    IncludeSpeaks     = true;                 // Include speaks
extern bool    IncludeHolidays   = false;                // Include holidays
extern string  FindKeyword       = "FOMC";                   // Find keyword
extern string  IgnoreKeyword     = "";                   // Ignore keyword
extern bool    AllowUpdates      = true;                 // Allow updates
extern int     UpdateHour        = 4;                    // Update every (in hours)
input string   lb_0              = "";                   // ------------------------------------------------------------
input string   lb_1              = "";                   // ------> PANEL SETTINGS
extern bool    ShowPanel         = true;                 // Show panel
extern bool    AllowSubwindow    = false;                // Show Panel in sub window
extern ENUM_BASE_CORNER Corner   = 2;                    // Panel side
extern string  PanelTitle = "Forex Calendar @ Forex Factory"; // Panel title
extern color   TitleColor        = C'46,188,46';         // Title color
extern bool    ShowPanelBG       = true;                 // Show panel backgroud
extern color   Pbgc              = C'25,25,25';          // Panel backgroud color
extern color   LowImpactColor    = C'91,192,222';        // Low impact color
extern color   MediumImpactColor = C'255,185,83';        // Medium impact color
extern color   HighImpactColor   = C'217,83,79';         // High impact color
extern color   HolidayColor      = clrOrchid;            // Holidays color
extern color   RemarksColor      = clrGray;              // Remarks color
extern color   PreviousColor     = C'170,170,170';       // Forecast color
extern color   PositiveColor     = C'46,188,46';         // Positive forecast color
extern color   NegativeColor     = clrTomato;            // Negative forecast color
extern bool    ShowVerticalNews  = true;                 // Show vertical lines
extern int     ChartTimeOffset   = -6;                    // Chart time offset (in hours)
extern int     EventDisplay      = 10;                   // Hide event after (in minutes)
input string   lb_2              = "";                   // ------------------------------------------------------------

input string   lb_4              = "";                   // ------------------------------------------------------------
input string   lb_5              = "";                   // ------> INFO SETTINGS
extern bool    ShowInfo          = true;                 // Show Symbol info ( Strength / Bar Time / Spread )
extern color   InfoColor         = C'255,185,83';        // Info color
extern int     InfoFontSize      = 10;                    // Info font size
input string   lb_6              = "";                   // ------------------------------------------------------------
input string   lb_7              = "";                   // ------> NOTIFICATION
input string   lb_8              = "";                   // *Note: Set (-1) to disable the Alert
extern int     Alert1Minutes     = 30;                   // Minutes before first Alert
extern int     Alert2Minutes     = 30;                   // Minutes before second Alert
extern bool    PopupAlerts       = true;                // Popup Alerts
extern bool    SoundAlerts       = true;                 // Sound Alerts
extern string  AlertSoundFile    = "news.wav";           // Sound file name
extern bool    EmailAlerts       = true;                // Send email
extern bool    NotificationAlerts = false;               // Send push notification


//------------------------------------------------------------------------------------------------------------
//--------------------------------------------- INTERNAL VARIABLE --------------------------------------------
//--- Vars and arrays
string xmlFileName;
string sData;
string Event[200][7];
string eTitle[10], eCountry[10], eImpact[10], eForecast[10], ePrevious[10];
int eMinutes[10];
datetime eTime[10];
int x0, xx1, xx2, xxf, xp;
int Factor = 2;
//--- Alert
bool FirstAlert;
bool SecondAlert;
datetime AlertTime;
//--- Buffers
double MinuteBuffer[];
double ImpactBuffer[];
//--- time
datetime xmlModifed;
int TimeOfDay;
datetime Midnight;
bool IsEvent;



//+------------------------------------------------------------------+
//|   GetCustomInfo                                                  |
//+------------------------------------------------------------------+
void GetCustomInfo(CustomInfo &info,
                   const int _error_code,
                   const ENUM_LANGUAGES _lang)
  {
   switch(_error_code)
     {
#ifdef __MQL5__
      case ERR_FUNCTION_NOT_ALLOWED:
         info.text1 = (_lang == LANGUAGE_EN) ? "The URL does not allowed for WebRequest" : "Этого URL нет в списке для WebRequest.";
         info.text2 = TELEGRAM_BASE_URL;
         break;
#endif
#ifdef __MQL4__
      case ERR_FUNCTION_NOT_CONFIRMED:
         info.text1 = (_lang == LANGUAGE_EN) ? "The URL does not allowed for WebRequest" : "Этого URL нет в списке для WebRequest.";
         info.text2 = TELEGRAM_BASE_URL;
         break;
#endif
      case ERR_TOKEN_ISEMPTY:
         info.text1 = (_lang == LANGUAGE_EN) ? "The 'Token' parameter is empty." : "Параметр 'Token' пуст.";
         info.text2 = (_lang == LANGUAGE_EN) ? "Please fill this parameter." : "Пожалуйста задайте значение для этого параметра.";
         break;
     }
  }


//+------------------------------------------------------------------+
//| Deinitialization                                                 |
//+------------------------------------------------------------------+
void OnDeinit3(const int reason)
  {
// Print(__FUNCTION__, " Terima Kasih - SignalForex.id");
//---
   for(int i = ObjectsTotal(); i >= 0; i--)
     {
      string name = ObjectName(i);
      if(StringFind(name, INAME) == 0)
         ObjectDelete(name);
     }
//--- Kill update timer only if removed
   if(reason == 1)
      EventKillTimer();
//---
  }
//+-----------------------------------------------------------------------------------------------+
//| Subroutine: to ID currency even if broker has added a prefix to the symbol, and is used to    |
//| determine the news to show, based on the users external inputs - by authors (Modified)        |
//+-----------------------------------------------------------------------------------------------+
bool IsCurrency(string symbol)
  {
//---
   for(int jk = 0; jk < SymbolsTotal(false); jk++)
      if(symbol == StringSubstr(SymbolName(jk, false), 0, 3))
         return(true);
   return(false);
//---
  }
//+------------------------------------------------------------------+
//| Converts ff time & date into yyyy.mm.dd hh:mm - by deVries       |
//+------------------------------------------------------------------+
string MakeDateTime(string strDate, string strTime)
  {
//---
   int n1stDash = StringFind(strDate, "-");
   int n2ndDash = StringFind(strDate, "-", n1stDash + 1);
   string strMonth = StringSubstr(strDate, 0, 2);
   string strDay = StringSubstr(strDate, 3, 2);
   string strYear = StringSubstr(strDate, 6, 4);
   int nTimeColonPos = StringFind(strTime, ":");
   string strHour = StringSubstr(strTime, 0, nTimeColonPos);
   string strMinute = StringSubstr(strTime, nTimeColonPos + 1, 2);
   string strAM_PM = StringSubstr(strTime, StringLen(strTime) - 2);
   int nHour24 = StrToInteger(strHour);
   if((strAM_PM == "pm" || strAM_PM == "PM") && nHour24 != 12)
      nHour24 += 12;
   if((strAM_PM == "am" || strAM_PM == "AM") && nHour24 == 12)
      nHour24 = 0;
   string strHourPad = "";
   if(nHour24 < 10)
      strHourPad = "0";
   return(StringConcatenate(strYear, ".", strMonth, ".", strDay, " ", strHourPad, nHour24, ":", strMinute));
//---
  }
//+------------------------------------------------------------------+
//| set impact Color - by authors                                    |
//+------------------------------------------------------------------+
color ImpactToColor(string impact)
  {
//---
   if(impact == "High")
      return (HighImpactColor);
   else
      if(impact == "Medium")
         return (MediumImpactColor);
      else
         if(impact == "Low")
            return (LowImpactColor);
         else
            if(impact == "Holiday")
               return (HolidayColor);
            else
               return (RemarksColor);
//---
  }
//+------------------------------------------------------------------+
//| Impact to number - by authors                                    |
//+------------------------------------------------------------------+
int ImpactToNumber(string impact)
  {
//---
   if(impact == "High")
      return(3);
   else
      if(impact == "Medium")
         return(2);
      else
         if(impact == "Low")
            return(1);
         else
            return(0);
//---
  }
//+------------------------------------------------------------------+
//| Convert day of the week to text                                  |
//+------------------------------------------------------------------+
string DayToStr(datetime time)
  {
   int ThisDay = TimeDayOfWeek(time);
   string day = "";
   switch(ThisDay)
     {
      case 0:
         day = "Sun";
         break;
      case 1:
         day = "Mon";
         break;
      case 2:
         day = "Tue";
         break;
      case 3:
         day = "Wed";
         break;
      case 4:
         day = "Thu";
         break;
      case 5:
         day = "Fri";
         break;
      case 6:
         day = "Sat";
         break;
     }
   return(day);
  }
//+------------------------------------------------------------------+
//| Convert months to text                                           |
//+------------------------------------------------------------------+
string MonthToStr()
  {
   int ThisMonth = Month();
   string month = "";
   switch(ThisMonth)
     {
      case 1:
         month = "Jan";
         break;
      case 2:
         month = "Feb";
         break;
      case 3:
         month = "Mar";
         break;
      case 4:
         month = "Apr";
         break;
      case 5:
         month = "May";
         break;
      case 6:
         month = "Jun";
         break;
      case 7:
         month = "Jul";
         break;
      case 8:
         month = "Aug";
         break;
      case 9:
         month = "Sep";
         break;
      case 10:
         month = "Oct";
         break;
      case 11:
         month = "Nov";
         break;
      case 12:
         month = "Dec";
         break;
     }
   return(month);
  }
  
    string  INAME="signal";
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
double Lots = GetLotSize(money_management);
enum ENUM_UNIT
  {
   InPips,                 // SL in pips
   InDollars               // SL in dollars
  };
/** Now, MarketData and MarketRates flags can change in real time, according with
 *  registered symbols and instruments.
 */

//+------------------------------------------------------------------+
//| Expert check license                                             |
//+------------------------------------------------------------------+
bool CheckLicense()
  {
   Print("Account name: ", AccountName());
   if(StringFind(StringLower(AccountName()), "account name in lowercase!!") < 0)
     {
      Alert("No license active!");
      Comment("No license active!");
      ExpertRemove();
      return false;
     }
   return true;
  }

//+------------------------------------------------------------------+
//| Expert string to lower                                           |
//+------------------------------------------------------------------+
string StringLower(string str)
  {
   string outstr = "ertyuio";
   string lower  = "abcdefghijklmnopqrstuvwxyz";
   string upper  = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
   for(int i = 0; i < StringLen(str); i++)
     {
      int t1 = StringFind(upper, StringSubstr(str, i, 1), 0);
      if(t1 >= 0)
        {
         outstr = outstr + StringSubstr(lower, t1, 1);
        }
      else
        {
         outstr = outstr + StringSubstr(str, i, 1);
        }
     }
   int op = FileOpen("licence.txt", 0, ',', CP_ACP);
   if(op > 0)
     {
      printf("File open");
     }
   else
     {
      printf("ERROR WECAN'T OPEN FILE license.txt");
     }
   return(outstr);
  }
  
  
  

extern double BreakEven_Points = 6;
int LotDigits; //initialized in OnInit

double MM_Percent = 1;
int MaxSlippage = 3; //slippage, adjusted in OnInit
double MaxTP = 100;
double MinTP = 75;
extern double CloseAtPL = 50;
bool crossed[4]; //initialized to true, used in function Cross
input int MaxOpenTrades = 3;
input int MaxLongTrades = 3;
input int MaxShortTrades = 3;
int MaxPendingOrders = 500;
int MaxLongPendingOrders = 1000;
int MaxShortPendingOrders = 1000;
input bool Hedging = false;
input int OrderRetry = 1; //# of retries if sending order returns error
input  int OrderWait = 3; //# of seconds to wait if sending order returns error
double myPoint; //initialized in OnInit

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
double MM_Size(double SL) //Risk % per trade, SL = relative Stop Loss to calculate risk
  {
   double MaxLot = MarketInfo(Symbol(), MODE_MAXLOT);
   double MinLot = MarketInfo(Symbol(), MODE_MINLOT);
   double tickvalue = MarketInfo(Symbol(), MODE_TICKVALUE);
   double ticksize = MarketInfo(Symbol(), MODE_TICKSIZE);
   double lots = (MM_Percent / 100) * SL / 2;
   if(lots > MaxLot)
      lots = MaxLot;
   if(lots < MinLot)
      lots = MinLot;
   return(lots);
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
double MM_Size_BO() //Risk % per trade for Binary Options
  {
   double MaxLot = MarketInfo(Symbol(), MODE_MAXLOT);
   double MinLot = MarketInfo(Symbol(), MODE_MINLOT);
   double tickvalue = MarketInfo(Symbol(), MODE_TICKVALUE);
   double ticksize = MarketInfo(Symbol(), MODE_TICKSIZE);
   return(MM_Percent * 1.0 / 100 * AccountBalance());
  }

void CloseTradesAtPL(double PL) //close all trades if total P/L >= profit (positive) or total P/L <= loss (negative)
  {
   double totalPL = TotalOpenProfit(0);
   if((PL > 0 && totalPL >= PL) || (PL < 0 && totalPL <= PL))
     {
      myOrderClose(Symbol(), OP_BUY, 100, "");
      myOrderClose(Symbol(), OP_SELL, 100, "");
     }
  }
  
  
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
int TradesCount(int type) //returns # of open trades for order type, current symbol and magic number
  {
   int result = 0;
   int total = OrdersTotal();
   for(int i = 0; i < total; i++)
     {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES) == false)
         continue;
      if(OrderMagicNumber() != MagicNumber || OrderSymbol() != Symbol() || OrderType() != type)
         continue;
      result++;
     }
   return(result);
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
double TotalOpenProfit(int direction)
  {
   double result = 0;
   int total = OrdersTotal();
   for(int i = 0; i < total; i++)
     {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         continue;
      if(OrderSymbol() != Symbol() || OrderMagicNumber() != MagicNumber)
         continue;
      if((direction < 0 && OrderType() == OP_BUY) || (direction > 0 && OrderType() == OP_SELL))
         continue;
      result += OrderProfit();
     }
   return(result);
  }
  
  

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void myOrderClose(string sym, int type, double volumepercent, string ordername) //close open orders for current symbol, magic number and "type" (OP_BUY or OP_SELL)
  {
   if(!IsTradeAllowed())
      return;
   if(type > 1)
     {
      myAlert(sym, "error", "Invalid type in myOrderClose");
      bot.SendMessage(ChatID, "Invalid type in myOrderClose");
      return;
     }
   bool success = false;
   int retries = 0;
   int err = 0;
   string ordername_ = ordername;
   if(ordername != "")
      ordername_ = "(" + ordername + ")";
   int total = OrdersTotal();
   ulong orderList[][2];
   int orderCount = 0;
   int i;
   for(i = 0; i < total; i++)
     {
      while(IsTradeContextBusy())
         Sleep(100);
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         continue;
      if(OrderMagicNumber() != MagicNumber || OrderSymbol() != sym || OrderType() != type)
         continue;
      orderCount++;
      ArrayResize(orderList, orderCount);
      orderList[orderCount - 1][0] = OrderOpenTime();
      orderList[orderCount - 1][1] = OrderTicket();
     }
   LotDigits = (int)MarketInfo(sym, MODE_LOTSIZE);
   if(orderCount > 0)
      ArraySort(orderList, WHOLE_ARRAY, 0, MODE_ASCEND);
   for(i = 0; i < orderCount; i++)
     {
      if(!OrderSelect((int)orderList[i][1], SELECT_BY_TICKET, MODE_TRADES))
         continue;
      while(IsTradeContextBusy())
         Sleep(100);
      RefreshRates();
      double price = (type == OP_SELL) ? MarketInfo(sym, MODE_ASK) : MarketInfo(sym, MODE_BID);
      double volume = NormalizeDouble(OrderLots() * volumepercent * 1.0 / 100, LotDigits);
      if(NormalizeDouble(volume, (int)MarketInfo(sym, MODE_LOTSIZE)) == 0)
         continue;
      success = false;
      retries = 0;
      while(!success && retries < OrderRetry + 1)
        {
         success = OrderClose(OrderTicket(), volume, NormalizeDouble(price, (int)MarketInfo(sym, MODE_DIGITS)), MaxSlippage, clrWhite);
         if(!success)
           {
            err = GetLastError();
            myAlert(sym, "print", "OrderClose" + ordername_ + " failed; error #" + IntegerToString(err) + " " + ErrorDescription(err));
            bot.SendMessage(ChatID, "OrderClose" + ordername_ + " failed; error #" + IntegerToString(err) + " " + ErrorDescription(err));
            Sleep(OrderWait * 1000);
           }
         retries++;
        }
      if(!success)
        {
         myAlert(sym, "error", "OrderClose" + ordername_ + " failed " + IntegerToString(OrderRetry + 1) + " times; error #" + IntegerToString(err) + " " + ErrorDescription(err));
         bot.SendMessage(ChatID, "OrderClose" + ordername_ + " failed " + IntegerToString(OrderRetry + 1) + " times; error #" + IntegerToString(err) + " " + ErrorDescription(err));
         return;
        }
     }
   string typestr[6] = {"Buy", "Sell", "Buy Limit", "Sell Limit", "Buy Stop", "Sell Stop"};
   if(success)
     {
      myAlert(sym, "order", "Orders closed" + ordername_ + ": " + typestr[type] + " " + sym + " Magic #" + IntegerToString(MagicNumber));
      bot.SendMessage(ChatID, "Orders closed" + ordername_ + ": " + typestr[type] + " " + sym + " Magic #" + IntegerToString(MagicNumber));
     }
  }
  void myAlert(string sym, string type, string message)
  {
   if(type == "print")
      Print(message);
   else
      if(type == "error")
        {
         Print(type + " | @  " + sym + "," + IntegerToString(Period()) + " | " + message);
         bot.SendMessage(ChatID, type + " | @  " + sym + "," + IntegerToString(Period()) + " | " + message);
        }
      else
         if(type == "order")
           {
           }
         else
            if(type == "modify")
              {
              }
  }
