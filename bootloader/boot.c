/*********************************************************************
 * Software License Agreement (BSD License)
 *
 * Copyright (c) 2018
 *
 * Balint Cristian <cristian dot balint at gmail dot com>
 *
 * TinnyModbus
 *
 *
 *  Redistribution and use in source and binary forms, with or without
 *  modification, are permitted provided that the following conditions
 *  are met:
 *
 *   * Redistributions of source code must retain the above copyright
 *     notice, this list of conditions and the following disclaimer.
 *
 *   * Redistributions in binary form must reproduce the above
 *     copyright notice, this list of conditions and the following
 *     disclaimer in the documentation and/or other materials provided
 *     with the distribution.
 *
 *   * Neither the name of the copyright holders nor the names of its
 *     contributors may be used to endorse or promote products derived
 *     from this software without specific prior written permission.
 *
 *  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 *  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 *  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
 *  FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 *  COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
 *  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
 *  BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 *  LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 *  CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 *  LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
 *  ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 *  POSSIBILITY OF SUCH DAMAGE.
 *
 *********************************************************************/

/*

  boot.c (BootLoader application)

*/

#include <stdio.h>
#include <stdlib.h>

#include <avr/io.h>
#include <avr/wdt.h>
#include <avr/eeprom.h>
#include <avr/pgmspace.h>
#include <avr/interrupt.h>

#include "crc16.h"
#include "eeprom.h"
#include "pgmflash.h"
#include "softuart.h"
#include "ws2812.h"

extern uint8_t IDModbus;

// modbus frames
uint8_t modbus[40];

static void send_modbus_array(uint8_t *sendbuff, const uint8_t len)
{
    // calc checksum
    uint16_t csum = clcCRC16(sendbuff, len - 2);

    // insert checksum
    sendbuff[len - 2] = csum & 0xFF;
    sendbuff[len - 1] = csum >> 8;

    // send over rs485 wire
    softuart_tx_array(&sendbuff[0], len);
}

static void send_modbus_exception(uint8_t *sendbuff, uint8_t errcode)
{
    sendbuff[1] += 0x80;   // exception flag
    sendbuff[2] = errcode; // exception code

    send_modbus_array(&sendbuff[0], 5);
}

int main(void)
{

    cli();

    wdt_disable();

    __asm volatile(
        // Always jmp into bootload
        "  ldi   r28,  lo8(__stack)                  \n\t"
        "  ldi   r29,  hi8(__stack)                  \n\t"
        "  out   0x3e, r29                           \n\t"
        "  out   0x3d, r28                           \n\t");

    softuart_tx_string("\n\nBOOTLOADER\n");

    // fetch uid from EEPROM
    uint8_t uid = eeprom_read_byte(&IDModbus);

    // set WS2812_PIN as output
    WS2812_DDR_REG |= WS2812_PIN_MASK;

    // display UID on LEDs
    ws2812_clear();
    ws2812_send_uid(uid);

    /*
     * receive buffer for modbus frame (fcode = 3,4,6)
     *  ____________________________________________
     * |   1x   |   1x   |   2x   |   2x   |   2x   |
     * |--------+--------+--------+--------+--------|
     * | S addr | F code | D addr | D nums | CRC16  |
     * |________|________|________|________|________|
     * modbus[32->39]
     */

    /*
     * receive ring buffer for modbus frame (fcode = 16)
     *  _____________________________________________________
     * |   1x   |   1x   |   2x   |   2x   |  32x   |   2x   |
     * |--------+--------+--------+--------+--------+--------|
     * | S addr | F code | D addr | D nums |  DATA  | CRC16  |
     * |________|________|________|________|________|________|
     * modbus[0->39]
     */

    uint8_t bytes_since_last_valid_frame = 0;

    for (;;)
    {

        // shift chain data to left
        for (uint8_t k = 1; k < 40; k++)
            modbus[k - 1] = modbus[k];

        // push into chain the new byte
        modbus[39] = softuart_rx(); // Receive a byte.
        bytes_since_last_valid_frame++;

        // is our address ?
        // is function code 10 ?
        // is amount of regs 16 ?
        if (((modbus[0] == uid) || (modbus[0] == 0)) &&
            (modbus[1] == 0x10) &&
            (modbus[5] == 0x10) &&
            (bytes_since_last_valid_frame > 39))
        {
            // is long crc valid ?
            uint16_t crc16 = modbus[38];
            crc16 |= (uint16_t)modbus[39] << 8;

            if (crc16 == clcCRC16(modbus, 38))
            {
                //
                // Process MODBUS command
                //

                // data address
                uint16_t daddr = modbus[3];
                daddr |= (uint16_t)modbus[2] << 8;

                // triage cmd
                switch (modbus[1])
                {

                // write multiple input register
                // (we receive pages of 32 octets)
                case 0x10:

                    // don't touch bootloader
                    // only chunks of 32 octet
                    if ((daddr <= 0x1BE0) &&
                        (daddr % 0x20 == 0))
                    {
                        // CD FF (RJMP 0x0DFF)
                        // overwrite start vector
                        // to point to bootloader
                        if (daddr == 0x0000)
                        {
                            modbus[6] = 0xFF;
                            modbus[7] = 0xCD;
                        }

                        // write page to flash
                        writePGMFlash(daddr);

                        // confirm with echo back
                        send_modbus_array(&modbus[0], 8);
                    }
                    else
                    {
                        // illegal address value
                        send_modbus_exception(&modbus[0], 0x02);
                    }

                    break; // fcode=0x10

                } // end switch fcode
                bytes_since_last_valid_frame = 0;
            } // end with valid crc
        }     // end valid modbus cmd

        // is our address ?
        // is function code valid ?
        // only 3,6 function code ?
        // only one register ?
        if (((modbus[32 + 0] == uid) ||
             (modbus[32 + 0] == 0)) &&
            ((modbus[32 + 1] == 0x03) ||
             (modbus[32 + 1] == 0x06)) &&
            (bytes_since_last_valid_frame > 7))
        {
            // is short crc valid ?
            uint16_t crc16 = modbus[32 + 6];
            crc16 |= (uint16_t)modbus[32 + 7] << 8;

            if (crc16 == clcCRC16(&modbus[32], 6))
            {
                //
                // Process MODBUS command
                //
                // data address
                uint16_t daddr = modbus[32 + 3];
                daddr |= (uint16_t)modbus[32 + 2] << 8;

                // data amount
                uint16_t dnums = modbus[32 + 5];
                dnums |= (uint16_t)modbus[32 + 4] << 8;

                // triage cmd
                switch (modbus[32 + 1])
                {

                case 0x06:

                    // change MODE
                    if (daddr == 0x0000)
                    {
                        // expect set value 0x0000
                        if ((modbus[32 + 4] == 0x00) &&
                            (modbus[32 + 5] == 0x00))
                        {
                            // confirm mode switch
                            softuart_tx_array(&modbus[32 + 0], 8);

                            // jump to main app
                            // @end of vector table
                            __asm volatile(
                                " ldi     r30, 0x0F  \n\t"
                                " ldi     r31, 0x00  \n\t"
                                " ijmp               \n\t");
                        }
                        else
                        {
                            // illegal data value
                            send_modbus_exception(&modbus[32 + 0], 0x03);
                        }
                    }

                    break; // fcode = 0x06

                } // end switch fcode
                bytes_since_last_valid_frame = 0;
            } // end with valid crc
        }     // end valid modbus cmd
    }         // end main loop

    return 0;
}