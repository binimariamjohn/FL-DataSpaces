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

#include "fl-experiment.h"
#include <random>
#include <chrono>
#include <memory>
#include <cstdlib>
#include <sys/stat.h>
#include <sys/types.h>

using sysclock_t = std::chrono::system_clock;

using namespace ns3;
uint16_t g_port = 9099;
std::unique_ptr<FLSimProvider> g_fLSimProvider;
std::map<int, std::shared_ptr<ClientSession> > g_clients;

NS_LOG_COMPONENT_DEFINE ("Wifi-Adhoc");

int main(int argc, char *argv[]) {

   //LogComponentEnable("PropagationLossModel", LOG_LEVEL_ALL);


    std::string clientDataRate = "250kbps";           /* Client upload rate (client -> server) */
    std::string serverDataRate = "1Mbps";             /* Server broadcast rate (server -> client) */
    int numClients = 20; //when numClients is 50 or greater, packets are not recieved by server
    std::string NetworkType = "wifi";
    int MaxPacketSize = 1024; //bytes
    double TxGain = 0.0; //dB + 30 = dBm
    double ModelSize = 1.500 * 10; // kb
    std::string learningModel = "sync";
    std::string modelName = "";
    std::string deviceType = "";
    double RoundMaxTimeS = 120.0;
    double ClientComputeDelayS = 0.0;


    CommandLine cmd(__FILE__);

    cmd.AddValue("NumClients", "Number of FL participating clients", numClients);
    cmd.AddValue("NetworkType", "Type of network", NetworkType);
    cmd.AddValue("MaxPacketSize", "Maximum size packet that can be sent", MaxPacketSize);
    cmd.AddValue("TxGain", "Power transmitted from clients and server", TxGain);
    cmd.AddValue("ModelSize", "Size of model", ModelSize);
    cmd.AddValue("ClientDataRate", "Client upload data rate (client to server)", clientDataRate);
    cmd.AddValue("ServerDataRate", "Server broadcast data rate (server to clients)", serverDataRate);
    cmd.AddValue("LearningModel", "Async or Sync federated learning", learningModel);
    cmd.AddValue("ModelName", "Model name label (optional)", modelName);
    cmd.AddValue("DeviceType", "Device type label (optional)", deviceType);
    cmd.AddValue("Port", "Port for Python FL coordination", g_port);
    cmd.AddValue("RoundMaxTimeS", "Max simulation time per FL round (seconds)", RoundMaxTimeS);
    cmd.AddValue("ClientComputeDelayS", "Client-side compute delay after receiving model (seconds)", ClientComputeDelayS);


    cmd.Parse(argc, argv);

    NS_LOG_UNCOND("[BOOT] Parsed args:"
                  << " NumClients=" << numClients
                  << " NetworkType=" << NetworkType
                  << " MaxPacketSize=" << MaxPacketSize
                  << " TxGain=" << TxGain
                  << " ModelSize(kB)=" << ModelSize
                  << " ClientDataRate=" << clientDataRate
                  << " ServerDataRate=" << serverDataRate
                  << " LearningModel=" << learningModel
                  << " ModelName=" << modelName
                  << " DeviceType=" << deviceType
                  << " Port=" << g_port);

    // Validate numClients
    if (numClients <= 0) {
        NS_LOG_UNCOND("ERROR: NumClients must be greater than 0. Got: " << numClients);
        return 1;
    }

    // Create FLSimProvider after parsing command line so it uses the correct port
    g_fLSimProvider = std::make_unique<FLSimProvider>(g_port);
    FLSimProvider *flSimProvider = g_fLSimProvider.get();

    bool bAsync = false;
    if (learningModel.compare("async") == 0) {
        bAsync = true;
    }


    ModelSize = ModelSize * 1000; // conversion to bytes

    NS_LOG_UNCOND(
            "{NumClients:" << numClients << ","
                            "NetworkType:" << NetworkType << ","
                            "MaxPacketSize:" << MaxPacketSize << ","
                    "ClientDataRate:" << clientDataRate << ","
                    "ServerDataRate:" << serverDataRate << ","
                            "TxGain:" << TxGain << ","
                    "ModelBytesCfg:" << static_cast<uint64_t>(ModelSize) << ","
                    "RoundMaxTimeS:" << RoundMaxTimeS << ","
                    "ClientComputeDelayS:" << ClientComputeDelayS << ","
                            "Port:" << g_port << "}"
    );
    //Experiment experiment(numClients,NetworkType,MaxPacketSize,TxGain);

    // Get logs directory from environment variable, default to current directory
    const char* logs_dir_env = std::getenv("LOGS_PATH");
    std::string logs_dir = (logs_dir_env != nullptr) ? logs_dir_env : ".";
    
    // Ensure logs directory exists
    mkdir(logs_dir.c_str(), 0755);

    std::time_t now = sysclock_t::to_time_t(sysclock_t::now());

    char buf[80] = { 0 };
    std::strftime(buf, sizeof(buf), "%Y-%m-%d_%H-%M-%S.csv", std::localtime(&now));

    char strbuff[256];
    snprintf(strbuff, 255, "%s/%s_%s_%.2f_%s",
             logs_dir.c_str(),
             learningModel.c_str(),
             NetworkType.c_str(),
             TxGain,
             buf);

    FILE *fp = fopen(strbuff, "w");
    if (fp == nullptr) {
        NS_LOG_UNCOND("ERROR: Could not open CSV file: " << strbuff);
        return 1;
    }

    // Write CSV header (network metrics as per paper: Li = tu + td + tc, Ti = br / tu)
    // Round, ClientID, ModelBytes, ReceiveStartS, ReceiveEndS, SendStartS, SendEndS, TdS, TcS, TuS, Throughput
    fprintf(fp, "Round,ClientID,ModelBytes,ReceiveStartS,ReceiveEndS,SendStartS,SendEndS,TdS,TcS,TuS,Throughput\n");
    fflush(fp);
    NS_LOG_UNCOND("CSV output file: " << strbuff);





    std::default_random_engine generator;
    std::uniform_real_distribution<double> r_dist(1.0, 4.0);
    //std::uniform_real_distribution<double> t_dist(0,1.0);

    //initialize structure for all clients
    for (int j = 0; j < numClients; j++) {

        //place the nodes at random spots from the base station

        double radius = (double) (5 << (j % 4 + 2));
        //double theta = t_dist(generator);
        double theta = (1.0 / numClients) * (j);

        g_clients[j] = std::shared_ptr<ClientSession>(new ClientSession(j, radius, theta));
    }

    ns3::Time timeOffset(0);

    if (flSimProvider) {
        NS_LOG_UNCOND("[SOCKET] Waiting for Python connection on port " << g_port);
        g_fLSimProvider->waitForConnection();
        NS_LOG_UNCOND("[SOCKET] Python connected!");
    } else {
        NS_LOG_UNCOND("[SOCKET][WARN] flSimProvider is null; running without Python control.");
    }


    int round = 0;
    while (true) {
        round ++;
        if (flSimProvider) {
            FLSimProvider::COMMAND::Type type = g_fLSimProvider->recv(g_clients);

            if (type == FLSimProvider::COMMAND::Type::EXIT) {
                g_fLSimProvider->Close();
                break;
            }
        }

        auto experiment = Experiment(numClients,
                                     NetworkType,
                                     MaxPacketSize,
                                     TxGain,
                                     ModelSize,
                                     clientDataRate,
                                     serverDataRate,
                                     bAsync,
                                     flSimProvider,
                                     fp,
                                     round,
                                     RoundMaxTimeS,
                                     ClientComputeDelayS
        );
        auto roundStats = experiment.WeakNetwork(g_clients, timeOffset);

        if (flSimProvider && !bAsync) {
            g_fLSimProvider->send(roundStats);
        }
        if (!flSimProvider) {
            break;
        }

        fflush(fp);

    }

    fclose(fp);

    return 0;
}
