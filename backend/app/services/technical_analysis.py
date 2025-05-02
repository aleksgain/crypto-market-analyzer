"""Technical analysis service for cryptocurrency price data."""

import logging
import pandas as pd
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

def calculate_technical_indicators(price_data, symbol):
    """Calculate technical indicators from price data.
    
    Args:
        price_data: Historical price data
        symbol: Cryptocurrency symbol
        
    Returns:
        dict: Technical indicators and signals
    """
    try:
        # Need at least 50 data points for meaningful indicators
        if len(price_data) < 50:
            logger.warning(f"Not enough price data for {symbol} to calculate technical indicators")
            return None
            
        # Convert to pandas DataFrame
        df = pd.DataFrame(price_data)
        
        # Make sure timestamp is a datetime object and sorted
        if isinstance(df['timestamp'][0], str):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
        df = df.sort_values('timestamp')
        
        # Calculate indicators
        # Simple Moving Averages
        df['SMA20'] = df['price'].rolling(window=20).mean()
        df['SMA50'] = df['price'].rolling(window=50).mean()
        
        # MACD
        df['EMA12'] = df['price'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['price'].ewm(span=26, adjust=False).mean()
        df['MACD'] = df['EMA12'] - df['EMA26']
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_hist'] = df['MACD'] - df['MACD_signal']
        
        # RSI
        delta = df['price'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['BB_middle'] = df['price'].rolling(window=20).mean()
        std_dev = df['price'].rolling(window=20).std()
        df['BB_upper'] = df['BB_middle'] + (std_dev * 2)
        df['BB_lower'] = df['BB_middle'] - (std_dev * 2)
        
        # Get latest values
        latest = df.iloc[-1].to_dict()
        
        # Generate trend signals
        sma_trend = 'bullish' if latest['SMA20'] > latest['SMA50'] else 'bearish'
        
        # MACD signal
        macd_signal = 'bullish' if latest['MACD'] > latest['MACD_signal'] else 'bearish'
        
        # MACD histogram direction (last 3 periods)
        if len(df) >= 3:
            hist_direction = 'bullish' if df['MACD_hist'].iloc[-1] > df['MACD_hist'].iloc[-2] > df['MACD_hist'].iloc[-3] else \
                            'bearish' if df['MACD_hist'].iloc[-1] < df['MACD_hist'].iloc[-2] < df['MACD_hist'].iloc[-3] else \
                            'neutral'
        else:
            hist_direction = 'neutral'
        
        # RSI signal
        if latest['RSI'] > 70:
            rsi_signal = 'overbought'
        elif latest['RSI'] < 30:
            rsi_signal = 'oversold'
        else:
            rsi_signal = 'neutral'
            
        # Bollinger Bands
        current_price = latest['price']
        bb_position = (current_price - latest['BB_lower']) / (latest['BB_upper'] - latest['BB_lower'])
        if bb_position > 0.8:
            bb_signal = 'overbought'
        elif bb_position < 0.2:
            bb_signal = 'oversold'
        else:
            bb_signal = 'neutral'
        
        # Support and resistance
        support_level = latest['BB_lower']
        resistance_level = latest['BB_upper']
        
        # Overall signal strength calculation
        bullish_signals = 0
        bearish_signals = 0
        
        # SMA trend
        if sma_trend == 'bullish':
            bullish_signals += 1
        else:
            bearish_signals += 1
            
        # MACD signal
        if macd_signal == 'bullish':
            bullish_signals += 1
        else:
            bearish_signals += 1
            
        # MACD histogram direction
        if hist_direction == 'bullish':
            bullish_signals += 0.5
        elif hist_direction == 'bearish':
            bearish_signals += 0.5
            
        # RSI signal
        if rsi_signal == 'oversold':
            bullish_signals += 1
        elif rsi_signal == 'overbought':
            bearish_signals += 1
            
        # Bollinger Bands signal
        if bb_signal == 'oversold':
            bullish_signals += 1
        elif bb_signal == 'overbought':
            bearish_signals += 1
            
        # Calculate overall signal and strength
        if bullish_signals > bearish_signals:
            overall_signal = 'bullish'
            signal_strength = bullish_signals / (bullish_signals + bearish_signals)
        elif bearish_signals > bullish_signals:
            overall_signal = 'bearish'
            signal_strength = bearish_signals / (bullish_signals + bearish_signals)
        else:
            overall_signal = 'neutral'
            signal_strength = 0.5
            
        # Format the result
        tech_signals = {
            'trend': {
                'sma_trend': sma_trend,
                'macd': macd_signal,
                'macd_histogram': hist_direction
            },
            'oscillators': {
                'rsi': rsi_signal,
                'bollinger': bb_signal
            },
            'levels': {
                'support': round(support_level, 2),
                'resistance': round(resistance_level, 2)
            },
            'values': {
                'rsi': round(latest['RSI'], 2),
                'macd': round(latest['MACD'], 4),
                'macd_signal': round(latest['MACD_signal'], 4),
                'sma20': round(latest['SMA20'], 2),
                'sma50': round(latest['SMA50'], 2)
            },
            'overall': {
                'signal': overall_signal,
                'strength': round(signal_strength, 2),
                'bullish_signals': bullish_signals,
                'bearish_signals': bearish_signals
            }
        }
        
        return tech_signals
        
    except Exception as e:
        logger.error(f"Error calculating technical indicators: {str(e)}")
        logger.exception("Technical analysis error")
        return None 