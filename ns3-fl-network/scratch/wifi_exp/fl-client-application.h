/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2022 Emily Ekaireb
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation;
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 * Author: Emily Ekaireb <eekaireb@ucsd.edu>
 */

#include "ns3/applications-module.h"
#include "ns3/type-id.h"
#include "ns3/application.h"
#include "ns3/event-id.h"
#include "ns3/ptr.h"
#include "ns3/traced-callback.h"
#include "ns3/address.h"
#include "ns3/inet-socket-address.h"
#include "ns3/seq-ts-size-header.h"
#include "ns3/performance-simple-model.h"

namespace ns3
{

  // Client-side model transfer.
  class ClientApplication : public Application {
   public:
    static TypeId GetTypeId (void);

    ClientApplication ();
    virtual ~ClientApplication ();
    void Setup (Ptr <Socket> socket, Address address, uint32_t packetSize, uint32_t nBytesModel,
                DataRate dataRate);

   private:
    virtual void StartApplication (void);
    virtual void StopApplication (void);

    void StartWriting ();
    void ConnectionSucceeded (Ptr <Socket> socket);
    void NormalClose (Ptr <Socket> socket);
    void ErrorClose (Ptr <Socket> socket);
    void ConnectionFailed (Ptr <Socket> socket);
    void HandleRead (Ptr <Socket> socket);
    void Send (Ptr <Socket> socket);
    void HandleReadyToSend (Ptr <Socket> sock, uint32_t available);

    Ptr <Socket> m_socket;
    Address m_peer;
    uint32_t m_packetSize;
    uint32_t m_bytesModel;
    DataRate m_dataRate;

    uint32_t m_bytesModelReceived;
    uint32_t m_bytesModelToReceive;
    Time m_timeBeginReceivingModelFromServer;
    Time m_timeEndReceivingModelFromServer;

    uint32_t m_bytesModelToSend;
    uint32_t m_bytesSent;

    EventId m_sendEvent;
    double m_computeDelayS;
    PerformanceSimpleModel m_model;
  };
}