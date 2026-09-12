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
#ifndef SERVER_H
#define SERVER_H

#include "ns3/application.h"
#include "ns3/event-id.h"
#include "ns3/ptr.h"
#include "ns3/traced-callback.h"
#include "ns3/address.h"
#include "ns3/inet-socket-address.h"
#include "ns3/seq-ts-size-header.h"
#include "ns3/data-rate.h"
#include <unordered_map>
#include <map>
#include <memory>
#include "fl-sim-interface.h"
#include "fl-energy.h"



namespace ns3 {

    class Address;
    class Socket;
    class Packet;

    // Server-side model transfer.
    class Server : public Application {

    public:
        class ClientSessionData {
        public:
                        ClientSessionData()
                                : m_bytesReceived(0),
                                    m_bytesSent(0),
                                    m_bytesModelToSend(0),
                                    m_bytesModelToReceive(0),
                                    m_bytesReceivedThisRound(0),
                                    m_bytesSentThisRound(0) {

            }

            ns3::Time m_timeBeginReceivingModelFromClient;
            ns3::Time m_timeEndReceivingModelFromClient;
            ns3::Time m_timeBeginSendingModelFromClient;
            ns3::Time m_timeEndSendingModelFromClient;
            uint32_t m_bytesReceived;
            uint32_t m_bytesSent;
            uint32_t m_bytesModelToSend;
            uint32_t m_bytesModelToReceive;
            uint32_t m_bytesReceivedThisRound;
            uint32_t m_bytesSentThisRound;
            ns3::Address m_address;

        };

        static TypeId GetTypeId(void);

        Server();
        virtual ~Server();

        std::map <Ptr<Socket>, std::shared_ptr<ClientSessionData>> GetAcceptedSockets(void) const;

        void SetClientSessionManager(ClientSessionManager *pSessionManager, FLSimProvider *fl_sim_provider, FILE *fp, int round) {
            m_clientSessionManager = pSessionManager;
            m_fLSimProvider = fl_sim_provider;
            m_fp=fp;
            m_round=round;
        }

    protected:
        virtual void DoDispose(void);


    private:
        virtual void StartApplication(void);
        virtual void StopApplication(void);

        void ReceivedDataCallback(Ptr <Socket> socket);
        void SendModel(Ptr <Socket> socket);
        void StartSendingModel(Ptr <Socket> socket);
        bool ConnectionRequestCallback(Ptr <Socket> s, const Address &from);
        void NewConnectionCreatedCallback(Ptr <Socket> socket, const Address &from);
        void ServerHandleSend(Ptr <Socket> sock, uint32_t available);
        void HandlePeerClose(Ptr <Socket> socket);
        void HandlePeerError(Ptr <Socket> socket);
        void PacketReceived(const Ptr <Packet> &p, const Address &from, const Address &localAddress);


    Ptr <Socket> m_socket;
    std::map <Ptr<Socket>, std::shared_ptr<ClientSessionData>> m_socketList;
    std::unordered_map<uint32_t, double> m_clientComputeDelays;  // Dynamic compute delays per client
    ClientSessionManager *m_clientSessionManager;
    Address m_local;
    uint64_t m_totalRx;
    TypeId m_tid;
    uint32_t m_packetSize;
    ns3::EventId m_sendEvent;
    uint32_t m_bytesModel;
    ns3::DataRate m_dataRate;
    bool m_bAsync;
    FLSimProvider *m_fLSimProvider;
    ns3::Time m_timeOffset;
    FILE *m_fp;
    int m_round;

    };

} // namespace ns3

#endif

