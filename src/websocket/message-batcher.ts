/**
 * WebSocket message batching system for improved performance
 */

import { WebSocket } from 'ws';
import { WebSocketMessage } from '../types';
import { config } from '../config';

export interface BatchedMessage {
  type: 'batch_update';
  messages: WebSocketMessage[];
  timestamp: number;
}

export interface ClientConnection {
  ws: WebSocket;
  userId?: string;
  subscriptions: Set<string>; // Canvas IDs or element IDs the client is subscribed to
  lastActivity: number;
}

/**
 * Message batcher for WebSocket communications
 */
export class MessageBatcher {
  private messageQueue: Map<string, WebSocketMessage[]> = new Map(); // clientId -> messages
  private batchTimer: NodeJS.Timeout | null = null;
  private clients: Map<WebSocket, ClientConnection> = new Map();

  constructor() {
    this.startBatchTimer();
  }

  /**
   * Add a client connection
   */
  addClient(ws: WebSocket, userId?: string): void {
    const client: ClientConnection = {
      ws,
      userId,
      subscriptions: new Set(),
      lastActivity: Date.now()
    };
    
    this.clients.set(ws, client);
    
    ws.on('close', () => {
      this.removeClient(ws);
    });

    ws.on('pong', () => {
      const client = this.clients.get(ws);
      if (client) {
        client.lastActivity = Date.now();
      }
    });
  }

  /**
   * Remove a client connection
   */
  removeClient(ws: WebSocket): void {
    const client = this.clients.get(ws);
    if (client) {
      // Clear any pending messages for this client
      this.messageQueue.delete(this.getClientId(ws));
      this.clients.delete(ws);
    }
  }

  /**
   * Subscribe a client to specific updates
   */
  subscribe(ws: WebSocket, subscriptionId: string): void {
    const client = this.clients.get(ws);
    if (client) {
      client.subscriptions.add(subscriptionId);
    }
  }

  /**
   * Unsubscribe a client from specific updates
   */
  unsubscribe(ws: WebSocket, subscriptionId: string): void {
    const client = this.clients.get(ws);
    if (client) {
      client.subscriptions.delete(subscriptionId);
    }
  }

  /**
   * Queue a message for batching
   */
  queueMessage(message: WebSocketMessage, targetClients?: WebSocket[]): void {
    const clients = targetClients || Array.from(this.clients.keys());
    
    for (const ws of clients) {
      if (this.shouldReceiveMessage(ws, message)) {
        const clientId = this.getClientId(ws);
        
        if (!this.messageQueue.has(clientId)) {
          this.messageQueue.set(clientId, []);
        }
        
        const queue = this.messageQueue.get(clientId)!;
        
        // Check for duplicate messages (e.g., same element update)
        if (!this.isDuplicateMessage(queue, message)) {
          queue.push(message);
          
          // Limit queue size per client
          if (queue.length > config.performance.websocketBatchSize) {
            queue.shift(); // Remove oldest message
          }
        }
      }
    }
  }

  /**
   * Send immediate message without batching
   */
  sendImmediate(message: WebSocketMessage, targetClients?: WebSocket[]): void {
    const clients = targetClients || Array.from(this.clients.keys());
    
    for (const ws of clients) {
      if (this.shouldReceiveMessage(ws, message) && ws.readyState === WebSocket.OPEN) {
        this.sendToClient(ws, message);
      }
    }
  }

  /**
   * Broadcast to all clients
   */
  broadcast(message: WebSocketMessage): void {
    this.queueMessage(message);
  }

  /**
   * Broadcast to specific canvas subscribers
   */
  broadcastToCanvas(message: WebSocketMessage, canvasId: string): void {
    const targetClients = Array.from(this.clients.entries())
      .filter(([ws, client]) => client.subscriptions.has(canvasId))
      .map(([ws]) => ws);
    
    this.queueMessage(message, targetClients);
  }

  /**
   * Get connection statistics
   */
  getStats(): {
    totalClients: number;
    authenticatedClients: number;
    queuedMessages: number;
    averageSubscriptions: number;
  } {
    const clients = Array.from(this.clients.values());
    const queuedMessages = Array.from(this.messageQueue.values())
      .reduce((total, queue) => total + queue.length, 0);
    const averageSubscriptions = clients.length > 0 ? 
      clients.reduce((total, client) => total + client.subscriptions.size, 0) / clients.length : 0;

    return {
      totalClients: clients.length,
      authenticatedClients: clients.filter(client => client.userId).length,
      queuedMessages,
      averageSubscriptions
    };
  }

  /**
   * Force flush all pending messages
   */
  flushAll(): void {
    this.flushBatches();
  }

  /**
   * Clean up inactive connections
   */
  cleanupInactiveConnections(): void {
    const now = Date.now();
    const timeout = 5 * 60 * 1000; // 5 minutes

    for (const [ws, client] of this.clients.entries()) {
      if (now - client.lastActivity > timeout) {
        if (ws.readyState === WebSocket.OPEN) {
          ws.ping();
        } else {
          this.removeClient(ws);
        }
      }
    }
  }

  private startBatchTimer(): void {
    this.batchTimer = setInterval(() => {
      this.flushBatches();
    }, config.performance.websocketBatchTimeoutMs);
  }

  private flushBatches(): void {
    for (const [clientId, messages] of this.messageQueue.entries()) {
      if (messages.length === 0) continue;

      const ws = this.getClientByClientId(clientId);
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        this.messageQueue.delete(clientId);
        continue;
      }

      if (messages.length === 1) {
        // Send single message directly
        this.sendToClient(ws, messages[0]);
      } else {
        // Send batched message
        const batchedMessage: BatchedMessage = {
          type: 'batch_update',
          messages,
          timestamp: Date.now()
        };
        this.sendToClient(ws, batchedMessage);
      }

      // Clear the queue
      this.messageQueue.set(clientId, []);
    }
  }

  private sendToClient(ws: WebSocket, message: WebSocketMessage | BatchedMessage): void {
    try {
      ws.send(JSON.stringify(message));
    } catch (error) {
      console.error('Failed to send WebSocket message:', error);
      this.removeClient(ws);
    }
  }

  private shouldReceiveMessage(ws: WebSocket, message: WebSocketMessage): boolean {
    const client = this.clients.get(ws);
    if (!client) return false;

    // Check if client is subscribed to this message
    if (message.type === 'element_updated' || message.type === 'element_created' || message.type === 'element_deleted') {
      // For element messages, check if subscribed to the canvas or element
      if (message.data?.canvasId && client.subscriptions.has(message.data.canvasId)) {
        return true;
      }
      if (message.data?.id && client.subscriptions.has(message.data.id)) {
        return true;
      }
    }

    // Global messages (like system announcements) go to all clients
    if (message.type === 'system_message' || message.type === 'canvas_cleared') {
      return true;
    }

    // If no specific subscriptions, send to all (backward compatibility)
    if (client.subscriptions.size === 0) {
      return true;
    }

    return false;
  }

  private isDuplicateMessage(queue: WebSocketMessage[], newMessage: WebSocketMessage): boolean {
    // Check for duplicate element updates
    if (newMessage.type === 'element_updated' && newMessage.data?.id) {
      return queue.some(msg => 
        msg.type === 'element_updated' && 
        msg.data?.id === newMessage.data?.id
      );
    }

    // Check for duplicate element deletions
    if (newMessage.type === 'element_deleted' && newMessage.data?.id) {
      return queue.some(msg => 
        msg.type === 'element_deleted' && 
        msg.data?.id === newMessage.data?.id
      );
    }

    return false;
  }

  private getClientId(ws: WebSocket): string {
    const client = this.clients.get(ws);
    return client?.userId || `anonymous_${ws.url || Math.random().toString(36)}`;
  }

  private getClientByClientId(clientId: string): WebSocket | undefined {
    for (const [ws, client] of this.clients.entries()) {
      const id = client.userId || `anonymous_${ws.url || Math.random().toString(36)}`;
      if (id === clientId) {
        return ws;
      }
    }
    return undefined;
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    if (this.batchTimer) {
      clearInterval(this.batchTimer);
      this.batchTimer = null;
    }
    
    this.messageQueue.clear();
    this.clients.clear();
  }
}

// Global message batcher instance
export const messageBatcher = new MessageBatcher();