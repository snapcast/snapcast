/***
    This file is part of snapcast
    Copyright (C) 2014-2025  Johannes Pohl

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
***/


// prototype/interface header file
#include "control_session_tcp.hpp"

// 3rd party headers
#include <boost/asio/read_until.hpp>
#include <boost/asio/write.hpp>

// local headers
#include "common/aixlog.hpp"
#include "server_settings.hpp"


using namespace std;

static constexpr auto LOG_TAG = "ControlSessionTCP";

// https://stackoverflow.com/questions/7754695/boost-asio-async-write-how-to-not-interleaving-async-write-calls/7756894


ControlSessionTcp::ControlSessionTcp(ControlMessageReceiver* receiver, tcp::socket&& socket, const ServerSettings& settings)
    : ControlSession(receiver, settings), socket_(std::move(socket)), strand_(boost::asio::make_strand(socket_.get_executor()))
{
    boost::system::error_code ec;
    auto peer = socket_.remote_endpoint(ec);
    peer_ = ec ? "unknown" : (peer.address().is_v6() ? "[" + peer.address().to_string() + "]" : peer.address().to_string()) + ":" + std::to_string(peer.port());
    auto local = socket_.local_endpoint(ec);
    local_ =
        ec ? "unknown" : (local.address().is_v6() ? "[" + local.address().to_string() + "]" : local.address().to_string()) + ":" + std::to_string(local.port());
}


ControlSessionTcp::~ControlSessionTcp()
{
    LOG(DEBUG, LOG_TAG) << "ControlSessionTcp::~ControlSessionTcp()\n";
    stop(); // NOLINT
}


void ControlSessionTcp::do_read()
{
    const std::string delimiter = "\n";
    boost::asio::async_read_until(socket_, streambuf_, delimiter,
                                  [this, self = shared_from_this(), delimiter](const boost::system::error_code& ec, std::size_t bytes_transferred)
    {
        if (ec)
        {
            if (ec == boost::asio::error::eof)
                LOG(INFO, LOG_TAG) << "Control peer " << peer_ << " closed connection to " << local_ << "\n";
            else if (ec == boost::asio::error::operation_aborted)
                LOG(DEBUG, LOG_TAG) << "Read canceled for control peer " << peer_ << " on " << local_ << "\n";
            else
                LOG(ERROR, LOG_TAG) << "Error reading control peer " << peer_ << " on " << local_ << ": " << ec.message() << "\n";
            return;
        }

        // Extract up to the first delimiter.
        std::string line{buffers_begin(streambuf_.data()), buffers_begin(streambuf_.data()) + bytes_transferred - delimiter.length()};
        if (!line.empty())
        {
            if (line.back() == '\r')
                line.resize(line.size() - 1);
            // LOG(DEBUG, LOG_TAG) << "received: " << line << "\n";
            if ((message_receiver_ != nullptr) && !line.empty())
            {
                message_receiver_->onMessageReceived(shared_from_this(), line, [this](const std::string& response)
                {
                    if (!response.empty())
                        sendAsync(response);
                });
            }
        }
        streambuf_.consume(bytes_transferred);
        do_read();
    });
}


void ControlSessionTcp::start()
{
    do_read();
}


void ControlSessionTcp::stop()
{
    if (!socket_.is_open())
        return;
    LOG(DEBUG, LOG_TAG) << "Stopping control peer " << peer_ << " on " << local_ << "\n";
    boost::system::error_code ec;
    socket_.shutdown(boost::asio::ip::tcp::socket::shutdown_both, ec);
    if (ec && ec != boost::asio::error::not_connected)
        LOG(ERROR, LOG_TAG) << "Error shutting down control peer " << peer_ << " on " << local_ << ": " << ec.message() << "\n";
    socket_.close(ec);
    if (ec)
        LOG(ERROR, LOG_TAG) << "Error closing control peer " << peer_ << " on " << local_ << ": " << ec.message() << "\n";
    LOG(DEBUG, LOG_TAG) << "ControlSession ControlSession stopped\n";
}


void ControlSessionTcp::sendAsync(const std::string& message)
{
    boost::asio::post(strand_, [this, self = shared_from_this(), message]()
    {
        messages_.emplace_back(message + "\r\n");
        if (messages_.size() > 1)
        {
            LOG(DEBUG, LOG_TAG) << "TCP session outstanding async_writes: " << messages_.size() << "\n";
            return;
        }
        send_next();
    });
}

void ControlSessionTcp::send_next()
{
    boost::asio::async_write(socket_, boost::asio::buffer(messages_.front()),
                             [this, self = shared_from_this()](boost::system::error_code ec, std::size_t length)
    {
        messages_.pop_front();
        if (ec)
        {
            if (ec == boost::asio::error::operation_aborted)
                LOG(DEBUG, LOG_TAG) << "Write canceled for control peer " << peer_ << " on " << local_ << "\n";
            else
                LOG(ERROR, LOG_TAG) << "Error writing control peer " << peer_ << " on " << local_ << ": " << ec.message() << "\n";
        }
        else
        {
            LOG(TRACE, LOG_TAG) << "Wrote " << length << " bytes to control socket\n";
        }
        if (!messages_.empty())
            send_next();
    });
}
