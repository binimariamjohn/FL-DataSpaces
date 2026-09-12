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
#include "ns3/address.h"
#include "ns3/address-utils.h"
#include "ns3/log.h"
#include "ns3/inet-socket-address.h"
#include "ns3/inet6-socket-address.h"
#include "ns3/node.h"
#include "ns3/socket.h"
#include "ns3/udp-socket.h"
#include "ns3/simulator.h"
#include "ns3/socket-factory.h"
#include "ns3/packet.h"
#include "ns3/trace-source-accessor.h"
#include "ns3/udp-socket-factory.h"
#include "fl-server.h"
#include "ns3/boolean.h"
#include "ns3/integer.h"
#include "ns3/uinteger.h"
#include "ns3/inet-socket-address.h"
#include "fl-sim-interface.h"

namespace ns3 {

    NS_LOG_COMPONENT_DEFINE ("Server");

    NS_OBJECT_ENSURE_REGISTERED (Server);

    TypeId
    Server::GetTypeId(void) {
        static TypeId tid = TypeId("ns3::Server")
                .SetParent<Application>()
                .SetGroupName("Applications")
                .AddConstructor<Server>()

                .AddAttribute("DataRate", "The data rate in on state.",
                              DataRateValue(DataRate("1b/s")),
                              MakeDataRateAccessor(&Server::m_dataRate),
                              MakeDataRateChecker())

                .AddAttribute("Local",
                              "The Address on which to Bind the rx socket.",
                              AddressValue(),
                              MakeAddressAccessor(&Server::m_local),
                              MakeAddressChecker())
                .AddAttribute("Protocol",
                              "The type id of the protocol to use for the rx socket.",
                              TypeIdValue(UdpSocketFactory::GetTypeId()),
                              MakeTypeIdAccessor(&Server::m_tid),
                              MakeTypeIdChecker())

                .AddAttribute("MaxPacketSize",
                              "MaxPacketSize to send to client",
                              TypeId::ATTR_SGC,
                              UintegerValue(),
                              MakeUintegerAccessor(&Server::m_packetSize),
                              MakeUintegerChecker<uint32_t>())
                .AddAttribute("Async",
                              "Run as async client",
                              TypeId::ATTR_SGC,
                              BooleanValue(false),
                              MakeBooleanAccessor(&Server::m_bAsync),
                              MakeBooleanChecker())
                .AddAttribute("BytesModel",
                              "Number of bytes in model",
                              TypeId::ATTR_SGC,
                              UintegerValue(),
                              MakeUintegerAccessor(&Server::m_bytesModel),
                              MakeUintegerChecker<uint32_t>())
                .AddAttribute("TimeOffset",
                              "Time offset to add to simulation time reported",
                              TypeId::ATTR_SGC,
                              TimeValue(),
                              MakeTimeAccessor(&Server::m_timeOffset),
                              MakeTimeChecker());


        return tid;
    }

    Server::Server() : m_packetSize(0), m_sendEvent(), m_bytesModel(0), m_bAsync(false), m_fLSimProvider(nullptr) {
        m_socket = 0;
    }

    Server::~Server() {
        NS_LOG_FUNCTION(this);
    }

    std::map <Ptr<Socket>, std::shared_ptr<Server::ClientSessionData>>
    Server::GetAcceptedSockets(void) const {
        NS_LOG_FUNCTION(this);
        return m_socketList;
    }

    void Server::DoDispose(void) {
        NS_LOG_FUNCTION(this);
        m_socket = 0;
        m_socketList.clear();

        // chain up
        Application::DoDispose();
    }

// Application Methods
    void Server::StartApplication()    // Called at time specified by Start
    {
        NS_LOG_FUNCTION(this);
        // Create the socket if not already
        if (!m_socket) {
            m_socket = Socket::CreateSocket(GetNode(), m_tid);
            if (m_socket->Bind(m_local) == -1) {
                NS_FATAL_ERROR("Failed to bind socket");
            }
            if (m_socket->Listen() == -1) {
                NS_FATAL_ERROR("Failed to listen socket");
            }
        }

        m_socket->SetRecvCallback(MakeCallback(&Server::ReceivedDataCallback, this));
        m_socket->SetAcceptCallback(
                MakeCallback(&Server::ConnectionRequestCallback, this),
                MakeCallback(&Server::NewConnectionCreatedCallback, this));
        m_socket->SetCloseCallbacks(
                MakeCallback(&Server::HandlePeerClose, this),
                MakeCallback(&Server::HandlePeerError, this));

    }

    void Server::StopApplication()     // Called at time specified by Stop
    {
        NS_LOG_FUNCTION(this);
        NS_LOG_UNCOND("Stopping Application");

        if (m_sendEvent.IsRunning()) {
            Simulator::Cancel(m_sendEvent);
        }

        //Close all connections
        for (auto const &itr: m_socketList) {
            itr.first->Close();
            itr.first->SetRecvCallback(MakeNullCallback < void, Ptr < Socket > > ());
        }

        if (m_socket) {
            m_socket->Close();
            m_socket->SetRecvCallback(MakeNullCallback < void, Ptr < Socket > > ());
        }

    }

    void Server::ReceivedDataCallback(Ptr <Socket> socket) {
        NS_LOG_FUNCTION(this << socket);
        Ptr <Packet> packet;
        Address from;
        Address localAddress;
        while ((packet = socket->RecvFrom(from))) {
            if (packet->GetSize() == 0) { //EOF
                break;
            }

            auto itr = m_socketList.find(socket);

            if (itr == m_socketList.end()) {
                return;
            }

            if (itr->second->m_bytesReceivedThisRound == 0) {
                itr->second->m_timeBeginReceivingModelFromClient = Simulator::Now();
            }

            itr->second->m_bytesReceived += packet->GetSize();
            itr->second->m_bytesReceivedThisRound += packet->GetSize();
            itr->second->m_bytesModelToReceive -= packet->GetSize();

            
            if (itr->second->m_bytesModelToReceive == 0) {
                itr->second->m_timeEndReceivingModelFromClient = Simulator::Now();

                const uint32_t clientId = m_clientSessionManager->ResolveToIdFromServer(socket);
                const uint32_t weightSizeBytes = m_bytesModel;

                const double receiveStart = itr->second->m_timeBeginSendingModelFromClient.GetSeconds();
                const double receiveEnd = itr->second->m_timeEndSendingModelFromClient.GetSeconds();
                const double sendStart = itr->second->m_timeBeginReceivingModelFromClient.GetSeconds();
                const double sendEnd = itr->second->m_timeEndReceivingModelFromClient.GetSeconds();

                // Td = download time (server -> client), Tc = compute delay, Tu = upload time (client -> server)
                const double tdS = receiveEnd - receiveStart;  // Time to receive full model
                const double tcS = sendStart - receiveEnd;     // Compute delay between download and upload
                const double tuS = sendEnd - sendStart;        // Time to send model back
                const double throughputKbps = (tuS > 0.0) ? ((weightSizeBytes * 8.0) / 1000.0 / tuS) : 0.0;

                // Round,ClientID,ModelBytes,ReceiveStartS,ReceiveEndS,SendStartS,SendEndS,TdS,TcS,TuS,Throughput
                fprintf(m_fp, "%i,%u,%u,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n",
                        m_round,
                        clientId,
                        weightSizeBytes,
                        receiveStart,
                        receiveEnd,
                        sendStart,
                        sendEnd,
                        tdS,
                        tcS,
                        tuS,
                        throughputKbps);
                fflush(m_fp);

                if (m_bAsync) {

                    if (m_fLSimProvider) {
                        FLSimProvider::AsyncMessage message;

                        message.id = m_clientSessionManager->ResolveToIdFromServer(socket);
                        // Keep existing async protocol fields in "offset" time-space.
                        const double offset = m_timeOffset.GetSeconds();
                        const double beginUplinkOff = sendStart + offset;
                        const double endUplinkOff = sendEnd + offset;
                        const double beginDownlinkOff = receiveStart + offset;

                        message.endTime = endUplinkOff;
                        message.startTime = beginDownlinkOff;
                        message.throughput = (endUplinkOff > beginUplinkOff)
                            ? (itr->second->m_bytesReceivedThisRound * 8.0 / 1000.0 / (endUplinkOff - beginUplinkOff))
                            : 0.0;

                        m_fLSimProvider->send(&message);

                    }

                    m_clientSessionManager->IncrementCycleCountFromServer(socket);

                    if (m_clientSessionManager->HasAllClientsFinishedFirstCycle() ||
                        (m_clientSessionManager->GetRound(socket) == 3)) {
                        m_clientSessionManager->Close();
                        if (m_fLSimProvider) {
                            m_fLSimProvider->end();
                        }

                        m_timeOffset = Simulator::Now() + Time(m_timeOffset.GetSeconds());
                        Simulator::Stop();
                    } else {
                        StartSendingModel(socket);
                    }
                } else {
                    // Sync mode: stop this ns-3 run once all participating clients finish the cycle.
                    m_clientSessionManager->IncrementCycleCountFromServer(socket);
                    if (m_clientSessionManager->HasAllClientsFinishedFirstCycle()) {
                        m_clientSessionManager->Close();
                        Simulator::Stop();
                    }
                }
            }

            socket->GetSockName(localAddress);

        }
    }

    void Server::HandlePeerClose(Ptr <Socket> socket) {
        NS_LOG_FUNCTION(this << socket);
    }

    void Server::HandlePeerError(Ptr <Socket> socket) {
        NS_LOG_FUNCTION(this << socket);
    }

    bool Server::ConnectionRequestCallback(Ptr <Socket> socket, const Address &address) {
        NS_LOG_FUNCTION(this << socket << address);
        return true;
    }


    void Server::NewConnectionCreatedCallback(Ptr <Socket> socket, const Address &from) {
        NS_LOG_FUNCTION(this << socket << from);
        auto clientSession = std::make_shared<ClientSessionData>();

        auto nsess = m_socketList.insert(std::make_pair(socket, clientSession));
        nsess.first->second->m_address = from;
        socket->SetRecvCallback(MakeCallback(&Server::ReceivedDataCallback, this));

        if (m_clientSessionManager) {
            // NS_LOG_UNCOND("NS3: accept clientId=" << m_clientSessionManager->ResolveToIdFromServer(socket));
        }
        StartSendingModel(socket);

        Ptr <Packet> packet;
        while ((packet = socket->Recv())) {
            if (packet->GetSize() == 0) {
                break; // EOF
            }
        }
    }

    void Server::ServerHandleSend(Ptr <Socket> socket, uint32_t available) {
        m_socket->SetSendCallback(MakeNullCallback < void, Ptr < Socket > , uint32_t > ());

        if (m_sendEvent.IsExpired()) {
            SendModel(socket);
        }
    }

    void Server::StartSendingModel(Ptr <Socket> socket) {
        auto itr = m_socketList.find(socket);
        itr->second->m_bytesModelToReceive = m_bytesModel;
        itr->second->m_bytesModelToSend = m_bytesModel;
        itr->second->m_bytesReceivedThisRound = 0;
        itr->second->m_bytesSentThisRound = 0;
        itr->second->m_timeBeginSendingModelFromClient = Time();
        itr->second->m_timeEndSendingModelFromClient = Time();
        itr->second->m_timeBeginReceivingModelFromClient = Time();
        itr->second->m_timeEndReceivingModelFromClient = Time();
        SendModel(socket);
    }

    void Server::SendModel(Ptr <Socket> socket) {

        //Check if send buffer has available space
        //If not, wait for data ready callback
        auto available = socket->GetTxAvailable();
        if (available == 0) {
            socket->SetSendCallback(MakeCallback(&Server::ServerHandleSend, this));
            return;
        }

        auto itr = m_socketList.find(socket);

        if (itr == m_socketList.end() || itr->second->m_bytesModelToSend == 0) {
            return;
        }

        auto bytes = std::min(std::min(
                itr->second->m_bytesModelToSend, available), m_packetSize);

        auto bytesSent = socket->Send(Create<Packet>(bytes));

        if (bytesSent == -1) {
            return;
        }

        if (bytesSent > 0 && itr->second->m_bytesSentThisRound == 0) {
            itr->second->m_timeBeginSendingModelFromClient = Simulator::Now();
        }

        itr->second->m_bytesSent += bytesSent;
        itr->second->m_bytesSentThisRound += bytesSent;
        
        if (itr->second->m_bytesSentThisRound % (20*1024*1024) == 0 || itr->second->m_bytesSentThisRound == bytesSent) {
        }
        itr->second->m_bytesModelToSend -= bytesSent;

        if (itr->second->m_bytesModelToSend) {
            Time nextTime(Seconds((bytes * 8) /
                                  static_cast<double>(m_dataRate.GetBitRate())));

            m_sendEvent = Simulator::Schedule(nextTime,
                                              &Server::SendModel, this, socket);
        }
        else
          {
            itr->second->m_timeEndSendingModelFromClient=Simulator::Now();
          }
    }

} // Namespace ns3
