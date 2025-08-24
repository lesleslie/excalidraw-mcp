/**
 * Authentication and authorization middleware
 */

import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { config } from '../config';

export interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    email?: string;
    roles?: string[];
  };
}

export interface TokenPayload {
  id: string;
  email?: string;
  roles?: string[];
  iat?: number;
  exp?: number;
}

/**
 * JWT Authentication middleware
 */
export function authenticateToken(req: AuthenticatedRequest, res: Response, next: NextFunction): void {
  // Skip authentication in development mode if disabled
  if (config.server.environment === 'development' && !config.security.authEnabled) {
    next();
    return;
  }

  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN

  if (!token) {
    res.status(401).json({ 
      success: false, 
      error: 'Access token required',
      code: 'AUTH_TOKEN_MISSING'
    });
    return;
  }

  try {
    const decoded = jwt.verify(token, config.security.jwtSecret) as TokenPayload;
    req.user = {
      id: decoded.id,
      email: decoded.email,
      roles: decoded.roles || []
    };
    next();
  } catch (error) {
    if (error instanceof jwt.TokenExpiredError) {
      res.status(401).json({ 
        success: false, 
        error: 'Token expired',
        code: 'AUTH_TOKEN_EXPIRED'
      });
    } else if (error instanceof jwt.JsonWebTokenError) {
      res.status(403).json({ 
        success: false, 
        error: 'Invalid token',
        code: 'AUTH_TOKEN_INVALID'
      });
    } else {
      res.status(500).json({ 
        success: false, 
        error: 'Authentication error',
        code: 'AUTH_ERROR'
      });
    }
  }
}

/**
 * Optional authentication middleware - allows both authenticated and anonymous access
 */
export function optionalAuth(req: AuthenticatedRequest, res: Response, next: NextFunction): void {
  // Skip authentication in development mode if disabled
  if (config.server.environment === 'development' && !config.security.authEnabled) {
    next();
    return;
  }

  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    next();
    return;
  }

  try {
    const decoded = jwt.verify(token, config.security.jwtSecret) as TokenPayload;
    req.user = {
      id: decoded.id,
      email: decoded.email,
      roles: decoded.roles || []
    };
  } catch (error) {
    // Continue without authentication for optional auth
  }

  next();
}

/**
 * Role-based authorization middleware
 */
export function requireRole(role: string) {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction): void => {
    if (!req.user) {
      res.status(401).json({ 
        success: false, 
        error: 'Authentication required',
        code: 'AUTH_REQUIRED'
      });
      return;
    }

    if (!req.user.roles || !req.user.roles.includes(role)) {
      res.status(403).json({ 
        success: false, 
        error: `Role '${role}' required`,
        code: 'AUTH_INSUFFICIENT_ROLE'
      });
      return;
    }

    next();
  };
}

/**
 * Generate JWT token
 */
export function generateToken(payload: Omit<TokenPayload, 'iat' | 'exp'>): string {
  return jwt.sign(
    payload,
    config.security.jwtSecret,
    {
      algorithm: config.security.jwtAlgorithm as jwt.Algorithm,
      expiresIn: `${config.security.tokenExpirationHours}h`
    }
  );
}

/**
 * Verify and decode JWT token
 */
export function verifyToken(token: string): TokenPayload | null {
  try {
    return jwt.verify(token, config.security.jwtSecret) as TokenPayload;
  } catch (error) {
    return null;
  }
}

/**
 * WebSocket authentication helper
 */
export function authenticateWebSocket(token: string): TokenPayload | null {
  if (config.server.environment === 'development' && !config.security.authEnabled) {
    return { id: 'anonymous' };
  }

  return verifyToken(token);
}