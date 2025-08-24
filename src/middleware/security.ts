/**
 * Security middleware for Express server
 */

import { Request, Response, NextFunction } from 'express';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import cors from 'cors';
import { config } from '../config';

/**
 * Configure CORS with secure settings
 */
export const corsMiddleware = cors({
  origin: (origin, callback) => {
    // Allow requests with no origin (like mobile apps or curl requests)
    if (!origin) {
      return callback(null, true);
    }

    if (config.security.allowedOrigins.indexOf(origin) !== -1) {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS policy'));
    }
  },
  credentials: config.security.corsCredentials,
  methods: config.security.corsMethods,
  allowedHeaders: config.security.corsHeaders,
  optionsSuccessStatus: 200, // Some legacy browsers choke on 204
});

/**
 * Configure security headers with Helmet
 */
export const securityHeaders = helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: [
        "'self'", 
        "'unsafe-inline'", // Required for Excalidraw
        "'unsafe-eval'",   // Required for some canvas operations
        "blob:"
      ],
      styleSrc: [
        "'self'", 
        "'unsafe-inline'", // Required for Excalidraw styling
        "https://fonts.googleapis.com"
      ],
      imgSrc: [
        "'self'", 
        "data:", 
        "blob:",
        "https:"
      ],
      connectSrc: [
        "'self'", 
        "ws:", 
        "wss:",
        config.server.environment === 'development' ? 'http://localhost:*' : ''
      ].filter(Boolean),
      fontSrc: [
        "'self'",
        "https://fonts.gstatic.com"
      ],
      objectSrc: ["'none'"],
      mediaSrc: ["'self'"],
      frameSrc: ["'none'"],
    },
  },
  crossOriginEmbedderPolicy: false, // Disable for Excalidraw compatibility
  hsts: {
    maxAge: 31536000,
    includeSubDomains: true,
    preload: true
  },
  noSniff: true,
  frameguard: { action: 'deny' },
  xssFilter: true,
  referrerPolicy: { policy: 'strict-origin-when-cross-origin' }
});

/**
 * Rate limiting middleware
 */
export const rateLimitMiddleware = rateLimit({
  windowMs: config.security.rateLimitWindowMinutes * 60 * 1000,
  max: config.security.rateLimitMaxRequests,
  message: {
    success: false,
    error: 'Too many requests from this IP, please try again later.',
    code: 'RATE_LIMIT_EXCEEDED'
  },
  standardHeaders: true,
  legacyHeaders: false,
  // Skip rate limiting in test environment
  skip: (req) => config.server.environment === 'test',
});

/**
 * Strict rate limiting for authentication endpoints
 */
export const authRateLimitMiddleware = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: config.server.environment === 'development' ? 100 : 5, // 5 attempts per 15 minutes in production
  message: {
    success: false,
    error: 'Too many authentication attempts, please try again later.',
    code: 'AUTH_RATE_LIMIT_EXCEEDED'
  },
  standardHeaders: true,
  legacyHeaders: false,
  skip: (req) => config.server.environment === 'test',
});

/**
 * Request size limiting middleware
 */
export function requestSizeLimit(req: Request, res: Response, next: NextFunction): void {
  const contentLength = req.get('content-length');
  const maxSize = 10 * 1024 * 1024; // 10MB limit
  
  if (contentLength && parseInt(contentLength, 10) > maxSize) {
    res.status(413).json({
      success: false,
      error: 'Request entity too large',
      code: 'REQUEST_TOO_LARGE'
    });
    return;
  }
  
  next();
}

/**
 * Security audit logging middleware
 */
export function auditLog(req: Request, res: Response, next: NextFunction): void {
  if (!config.logging.auditEnabled) {
    next();
    return;
  }

  const start = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    const auditEntry = {
      timestamp: new Date().toISOString(),
      method: req.method,
      url: req.url,
      statusCode: res.statusCode,
      userAgent: req.get('User-Agent'),
      ip: req.ip,
      duration,
      userId: (req as any).user?.id || 'anonymous'
    };
    
    // Log suspicious activities
    if (res.statusCode >= 400 || duration > 5000) {
      console.log('[AUDIT]', JSON.stringify(auditEntry));
    }
  });
  
  next();
}

/**
 * Error handling middleware that prevents information leakage
 */
export function secureErrorHandler(error: any, req: Request, res: Response, next: NextFunction): void {
  // Log the full error for debugging
  console.error('Server error:', error);
  
  // Don't leak error details in production
  const isDevelopment = config.server.environment === 'development';
  
  const errorResponse = {
    success: false,
    error: isDevelopment ? error.message : 'Internal server error',
    code: error.code || 'INTERNAL_ERROR',
    ...(isDevelopment && { stack: error.stack })
  };
  
  res.status(error.status || 500).json(errorResponse);
}