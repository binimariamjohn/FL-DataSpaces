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
#ifndef SERVER_HELPER_H
#define SERVER_HELPER_H

#include "ns3/object-factory.h"
#include "ns3/ipv4-address.h"
#include "ns3/node-container.h"
#include "ns3/application-container.h"

namespace ns3 {

    // Server app installer.
    class ServerHelper {
    public:
        ServerHelper(std::string protocol, Address address);
        void SetAttribute(std::string name, const AttributeValue &value);
        ApplicationContainer Install(NodeContainer c) const;
        ApplicationContainer Install(Ptr <Node> node) const;
        ApplicationContainer Install(std::string nodeName) const;

    private:
        Ptr <Application> InstallPriv(Ptr <Node> node) const;

        ObjectFactory m_factory;
    };

} // namespace ns3

#endif /* PACKET_SINK_HELPER_H */
